# src/qeg_nmr_qua/experiment/experiment.py
from collections.abc import Iterable
from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.config.settings import ExperimentSettings
from qeg_nmr_qua.config.config_from_settings import cfg_from_settings
from qeg_nmr_qua.experiment.macros import (
    readout_mode,
    safe_mode,
    drive_mode,
    AMPLIFIER_BLANKING_TIME,
    RX_SWITCH_DELAY,
)

import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from scipy import signal

from qm import QuantumMachinesManager
from qm import SimulationConfig
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.plot import interrupt_on_close
from qualang_tools.results.data_handler import DataHandler
from qualang_tools.units import unit
from qm.qua import (
    play,
    wait,
    measure,
    save,
    program,
    declare,
    stream_processing,
    declare_stream,
    for_,
    fixed,
    demod,
    frame_rotation_2pi,
    align,
    amp,
)

u = unit(coerce_to_integer=True)


class Experiment:
    def __init__(self, settings: ExperimentSettings, config: OPXConfig = None):
        """
        Initializes the base experiment class with default configurations and containers for commands, results,
        plotting data, and experimental delays. This class serves as a foundational structure for conducting
        experiments.

        Experimental-style specific setting should be implemented in subclasses.

        """
        self.settings = settings

        # check if a config is provided, else create from settings.
        # in the future this should verify the config matches the settings.
        self.config = config if config is not None else cfg_from_settings(settings)

        # ---- Experiment parameters ---- #
        self.n_avg = settings.n_avg
        self.pi_half_pulse = settings.pi_half_key

        self.probe_key = settings.res_key
        self.helper_key = settings.helper_key
        self.amplifier_key = settings.amp_key
        self.rx_switch_key = settings.sw_key

        self.pre_scan_delay = (
            settings.readout_delay // 4 - 2 * AMPLIFIER_BLANKING_TIME - RX_SWITCH_DELAY
        )
        if self.pre_scan_delay < 16:
            raise ValueError("Readout delay too short to accommodate switching times.")

        self.readout_len = settings.dwell_time
        self.tau_min = settings.readout_start
        self.tau_max = settings.readout_end
        self.measure_sequence_len = (self.tau_max - self.tau_min) // self.readout_len
        self.tau_sweep = np.arange(
            0.5 * self.readout_len,
            (self.measure_sequence_len + 0.5) * self.readout_len,
            self.readout_len,
        )
        self.loop_wait_cycles = self.readout_len // 4  # to clock cycles

        self.wait_between_scans = settings.thermal_reset // 4  # 5 T1 in clock cycles

        self.qmm = QuantumMachinesManager(
            self.config.qop_ip, cluster_name=self.config.cluster
        )

        # command parameters
        self._commands = []  # list of commands to build the experiment, FIFO
        self.use_fixed = False  # whether to use fixed point for looping variables
        self.var_vec = None  # variable vector for looped experiments
        self.start_with_wait = True  # whether to start the experiment with a wait

        # ---- Data to save ---- #
        self.save_data_dict = {
            "n_avg": self.n_avg,
            "config": config,
        }
        self.save_dir = Path(__file__).resolve().parent / "data"

    def add_pulse(
        self,
        name: str,
        element: str,
        phase: float = 0.0,
        amplitude: float = 1.0,
        length: int | Iterable | None = None,
    ):
        """
        Adds a pulse command to the experiment. Stores the data to control the pulse in the experiment's command list,
        and ensures the command is well defined

        Args:
            name (str): Name of the pulse operation, must be defined in the element's config.
            element (str): Element to which the pulse is applied. Must be defined in the config.
            phase (float | Iterable): Phase of the pulse in degrees.
            amplitude (float | Iterable): Amplitude of the pulse. This factor multiplies the waveform's defined amplitude.
            length (int | Iterable): Length of the pulse in nanoseconds. This overrides the waveform's defined length.
        """
        if element not in self.config.elements.elements.keys():
            raise ValueError(f"Element {element} not defined in config.")
        if name not in self.config.elements.elements[element].operations.keys():
            raise ValueError(f"Operation {name} not defined for element {element}.")

        command = {
            "type": "pulse",
            "name": name,
            "element": element,
        }
        if isinstance(phase, Iterable):
            command["length"] = length // 4 if length is not None else None
            command["amplitude"] = amplitude
            self.update_loop((np.array(phase) / 360) % 1)
            self.use_fixed = True
        elif isinstance(amplitude, Iterable):
            command["length"] = length // 4 if length is not None else None
            command["phase"] = (phase / 360) % 1
            self.update_loop(np.array(amplitude))
            self.use_fixed = True
        elif isinstance(length, Iterable):
            command["phase"] = (phase / 360) % 1
            command["amplitude"] = amplitude
            self.update_loop(np.array(length) // 4)
            self.use_fixed = False
        else:
            command["phase"] = (phase / 360) % 1  # convert to fraction of 2pi
            command["amplitude"] = amplitude
            command["length"] = length // 4 if length is not None else None

        self._commands.append(command)

    def add_delay(self, duration: int):
        """
        Adds a delay command to the experiment. Stores the data to control the delay in the experiment's command list.

        Args:
            duration (int | Iterable): Duration of the delay in nanoseconds.
        """
        command = {
            "type": "delay",
            # "duration": duration // 4,  # convert to clock cycles
        }
        if isinstance(duration, Iterable):
            self.update_loop(np.array(duration) // 4)
            self.use_fixed = False
        else:
            command["duration"] = duration // 4  # convert to clock cycles

        self._commands.append(command)

    def add_align(self, elements: list[str] | None = None):
        """
        Adds an align command to the experiment. Stores the data to control the alignment in the experiment's command list.

        Args:
            elements (list[str]): List of elements to align.
        """
        if elements is not None:
            for el in elements:
                if el not in self.config.elements:
                    raise ValueError(f"Element {el} not defined in config.")
        command = {
            "type": "align",
            "elements": elements,
        }
        self._commands.append(command)

    def remove_initial_delay(self):
        """
        Removes the 5 T1 delay from the start of the sequence. Useful for testing with the
        simulator, but should be generally used to ensure proper thermalization between
        experiments.
        """
        self.start_with_wait = False

    def update_loop(self, var_vec):
        """
        Updates the variable vector for the experiment. This is used to define the loop
        that the experiment will run over. If the variable vector is already defined, this
        function will check that the new vector is consistent with the previous one by determining
        if the new vector is a constant multiple of the old one.

        For internal use only - will have dramatic mutation side effects otherwise.

        Args:
            var_vec (array): Array of values for the variable in the experiment

        Returns:
            float: The constant multiple of the new vector to the old vector, 1 if this is the first update.

        Raises:
            ValueError: Throws an error if the new vector is not a constant multiple of the old one, or if
                the new vector is all zeros.
        """
        if np.all(var_vec == 0):
            raise ValueError("Variable vector cannot be all zeros.")
        if self.var_vec is None:
            self.var_vec = var_vec
            return 1

        two = self.var_vec
        if np.dot(var_vec, two) * np.dot(two, var_vec) == np.dot(
            var_vec, var_vec
        ) * np.dot(two, two):
            div = -1
            idx = 0
            while div < 0:
                div = two[idx] / var_vec[idx] if var_vec[idx] != 0 else -1
                idx += 1
            if div > 0:
                return div

        raise ValueError("Inconsistent loop variables.")

    def translate_command(self, command: dict):
        """
        Translates a command dictionary into QUA code.

        Args:
            command (dict): Command dictionary to translate.

        Raises:
            ValueError: If the command type is unknown.
        """
        if command["type"] == "pulse":
            frame_rotation_2pi(command["phase"] / 360, command["element"])
            play(
                command["name"] * amp(command["amplitude"]),
                command["element"],
            )
            frame_rotation_2pi(-command["phase"] / 360, command["element"])
        elif command["type"] == "delay":
            wait(command["duration"])
        elif command["type"] == "align":
            align(*command["elements"]) if command["elements"] is not None else align()
        else:
            raise ValueError(f"Unknown command type: {command['type']}")

    def create_experiment(self):
        """
        Creates the Quantum Machine program for the experiment, and returns the
        experiment object as a qua `program`. This is used by the `execute_experiment` and
        `simulate_experiment` methods.

        Returns:
            program: The QUA program for the experiment defined by this class's commands.
        """
        pass  # to be implemented by subclasses

    def simulate_experiment(self, sim_length=10_000):
        """
        Simulates the experiment using the configured experiment defined by this class based on the current
        config defined by this instance's `config` attribute. The simulation returns the generated waveforms
        of the experiment up to the duration `sim_length` in ns. Useful for checking the timings before running
        on hardware.

        Parameters:
            sim_length (int, optional): The duration of the simulation in ns. Defaults to 10_000.
            n_avg (int, optional): The number of averages per point. Defaults to 100_000.
            measure_contrast (bool): If True, only the |0> state is measured, if False, both |0> and |1> are measured.

        Raises:
            ValueError: Throws an error if insufficient details about the experiment are defined.
        """
        if len(self._commands) == 0:
            raise ValueError("No commands have been added to the experiment.")
        expt = self.create_experiment()
        simulation_config = SimulationConfig(
            duration=sim_length // 4
        )  # Simulate blocks python until the simulation is done
        job = self.qmm.simulate(self.config.to_opx_config(), expt, simulation_config)
        # Get the simulated samples
        samples = job.get_simulated_samples()
        # Plot the simulated samples
        samples.con1.plot()
        # Get the waveform report object
        waveform_report = job.get_simulated_waveform_report()
        # Cast the waveform report to a python dictionary
        waveform_dict = waveform_report.to_dict()
        # Visualize and save the waveform report
        waveform_report.create_plot(
            samples, plot=True, save_path=str(Path(__file__).resolve())
        )
        return job

    def execute_experiment(self):
        """
        Executes the experiment using the configured experiment defined by this class based on the current
        config defined by this instance's `config` attribute. The method handles the execution on hardware,
        data fetching, and basic plotting of results.

        Raises:
            ValueError: Throws an error if insufficient details about the experiment are defined.
        """
        if len(self._commands) == 0:
            raise ValueError("No commands have been added to the experiment.")

        expt = self.create_experiment()
        qm = self.qmm.open_qm(self.config.to_opx_config(), close_other_machines=True)
        job = qm.execute(expt)
        self.live_plot(qm, job)

    def live_plot(self, qm, job):
        """
        Live plots the results of the experiment as it is being executed.
        """
        pass  # to be implemented by subclasses
