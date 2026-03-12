# src/qeg_nmr_qua/experiment/experiment.py
from collections.abc import Iterable
import warnings
import math

from pyparsing import Any
from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.config.settings import ExperimentSettings
from qeg_nmr_qua.config.config_from_settings import cfg_from_settings
from qeg_nmr_qua.analysis.data_saver import DataSaver
from qeg_nmr_qua.experiment.macros import (
    AMPLIFIER_BLANKING_TIME,
    RX_SWITCH_DELAY,
)

import numpy as np
from pathlib import Path
from qm import (
    QuantumMachinesManager,
    SimulationConfig,
    QuantumMachine,
    generate_qua_script,
)
from qm.jobs.running_qm_job import RunningQmJob
from qualang_tools.units import unit
from qm.qua import play, wait, frame_rotation_2pi, align, amp, for_, declare, fixed

u = unit(coerce_to_integer=True)


class Experiment:
    """
    Base class for conducting NMR experiments on the OPX-1000.

    This class manages quantum machine configurations, experiment commands (pulses, delays, alignments),
    and data collection. It provides a structured interface for building and executing pulse sequences
    with support for looped experiments and real-time data acquisition.

    Subclasses should implement experiment-specific logic in:

    - ``create_experiment()``: Build the QUA program from stored commands
    - ``validate_experiment()``: Validate settings and command consistency
    - ``data_processing()``: Handle real-time data during hardware execution

    Typical workflow:

    1. Create an Experiment subclass instance with relevant settings and config
    2. Build sequence: add pulses, delays, and alignments using ``add_*`` methods
    3. Test: call ``simulate_experiment()`` to verify timing and waveforms
    4. Execute: call ``execute_experiment()`` to run on hardware
    5. Save: call ``save_data()`` to persist configuration, settings, and results

    Attributes:
        settings: Experiment-specific parameters (frequencies, pulse lengths, etc.)
        config: OPX configuration object
        save_dir: Directory to save experiment data
        save_data_dict: Dictionary which contains data extracted during the experiment for saving
        qmm: ``QuantumMachinesManager`` instance for managing connection to the OPX-1000
    """

    def __init__(
        self,
        settings: ExperimentSettings,
        config: OPXConfig = None,
        connect: bool = True,
    ):
        """
        Initialize experiment with configuration and settings.

        Args:
            settings: Experiment-specific parameters (frequencies, pulse lengths, etc.).
            config: OPX configuration. If None, automatically generated from settings.
            connect (bool): Whether to establish a live connection to the OPX-1000 via
                ``QuantumMachinesManager``. Set to ``False`` for offline compilation or
                unit testing. Defaults to ``True``.

        Raises:
            ValueError: If readout delay is too short to accommodate switching times.
        """
        self.settings = settings

        # check if a config is provided, else create from settings.
        # in the future this should verify the config matches the settings.
        self.config = config if config is not None else cfg_from_settings(settings)

        # ---- Experiment parameters ---- #
        self.n_avg = settings.n_avg
        self.pulse_shape = settings.pulse_shape

        self.probe_key = settings.res_key
        self.helper_key = settings.helper_key
        self.amplifier_key = settings.amp_key
        self.rx_switch_key = settings.sw_key

        self.pre_scan_delay = (
            settings.readout_delay // 4 - AMPLIFIER_BLANKING_TIME - 2 * RX_SWITCH_DELAY
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

        if connect:
            self.qmm = QuantumMachinesManager(
                self.config.qop_ip, cluster_name=self.config.cluster
            )

        # command parameters
        self._commands = []  # list of commands to build the experiment, FIFO
        self.use_fixed_lst = []  # whether to use fixed point for looping variables
        self.var_vec_lst = []  # variable vector for looped experiments
        self.start_with_wait = True  # whether to start the experiment with a wait
        self.use_frame_change = False
        self.frame_change_angle = 0.0  # angle for frame change compensation
        self.frame_change_elements = ("",)  # element(s) for frame change compensation

        # ---- Data to save ---- #
        self.save_data_dict = {
            "n_avg": self.n_avg,
        }
        self.save_dir = (
            Path(__file__).resolve().parent / "data"
            if settings.save_dir is None
            else settings.save_dir
        )
        self.data_saver = DataSaver(self.save_dir)

    def add_pulse(
        self,
        element: str,
        shape: str = None,
        phase: float | Iterable = 0.0,
        amplitude: float | Iterable = 1.0,
        length: int | Iterable | None = None,
        phase_cycle: bool = False,
        loop_layer: int = -1,
    ):
        """
        Adds a pulse command to the experiment. Stores the data to control the pulse in the experiment's command list,
        and ensures the command is well defined. Timings are converted from ns and stored in clock cycles (4 ns).

        Each of ``phase``, ``amplitude``, and ``length`` may independently be a scalar or an iterable.
        When iterable, the parameter is treated as a swept variable and assigned its own loop layer.
        Multiple parameters may be swept simultaneously in a single call — each will be auto-assigned to
        its own layer (or a shared layer if the vectors are proportional), enabling multi-dimensional sweeps::

            # All three swept independently → 3 loop layers
            expt.add_pulse(element, phase=[0, 90, 180], amplitude=[0.9, 1.0, 1.1], length=[1000, 1100, 1200])

        Args:
            element (str): Element to which the pulse is applied. Must be defined in the config.
            shape (str): Shape of the pulse operation, defaults to ``settings.pulse_shape`` if not provided.
            phase (float | Iterable): Phase of the pulse in degrees. Stored as a fraction of 2π.
            amplitude (float | Iterable): Amplitude scale factor for the pulse waveform.
            length (int | Iterable): Length of the pulse in nanoseconds, overriding the waveform default.
            phase_cycle (bool): Whether to vary the phase in the averaging loop for phase cycling.
            loop_layer (int): Loop layer (1-based) to associate with all swept parameters in this call.
                Use ``-1`` (default) to auto-assign each swept parameter to the first available layer
                (or reuse an existing layer if the vector is proportional to one already stored).
        """
        if element not in self.config.elements.elements.keys():
            raise ValueError(f"Element {element} not defined in config.")

        pulse = self.config.elements.elements[element].operations.get(shape, None)
        if shape is None:
            shape = self.pulse_shape
            pulse = self.config.elements.elements[element].operations.get(
                self.pulse_shape, None
            )
        elif pulse is None:
            raise ValueError(
                f"Pulse shape '{shape}' not recognized in element '{element}'. "
                f"Please provide a valid pulse shape key."
            )

        command = {
            "type": "pulse",
            "shape": shape,
            "element": element,
        }

        # Handle phase -- swept, phase-cycled, or constant
        if phase_cycle:
            if isinstance(phase, Iterable):
                command["phase_cycle"] = (np.array(phase) / 360) % 1
            else:
                raise ValueError(
                    "Phase cycling requires an iterable of phases, found a scalar instead."
                )
        else:
            if isinstance(phase, Iterable):
                layer, div = self._update_loop((np.array(phase) / 360) % 1, loop_layer)
                self._update_loop_type(layer, use_fixed=True)
                command["phase_layer"] = layer
                command["phase_scale"] = div
            else:
                command["phase"] = (phase / 360) % 1  # convert to fraction of 2pi

        # Handle amplitude -- swept or fixed
        if isinstance(amplitude, Iterable):
            layer, div = self._update_loop(np.array(amplitude), loop_layer)
            self._update_loop_type(layer, use_fixed=True)
            command["amplitude_layer"] = layer
            command["amplitude_scale"] = div
        else:
            command["amplitude"] = amplitude

        # Handle length -- swept or fixed
        if isinstance(length, Iterable):
            layer, div = self._update_loop(np.array(length, dtype=int) // 4, loop_layer)
            self._update_loop_type(layer, use_fixed=False)
            command["length_layer"] = layer
            command["length_scale"] = div
        else:
            command["length"] = (
                length // 4
                if length is not None
                else self.config.pulses.pulses[pulse].length // 4
            )
        self._commands.append(command)

    def add_delay(self, duration: int | Iterable, loop_layer: int = -1):
        """
        Adds a delay command to the experiment. Stores the data to control the delay in the experiment's command list.

        Args:
            duration (int | Iterable): Duration of the delay in nanoseconds.
            loop_layer (int): Loop layer (1-based) to associate with the swept duration.  Use ``-1``
                (default) to auto-assign to the first available layer.
        """
        command = {
            "type": "delay",
        }
        if isinstance(duration, Iterable):
            layer, div = self._update_loop(
                np.array(duration, dtype=int) // 4, loop_layer
            )
            self._update_loop_type(layer, use_fixed=False)
            command["layer"] = layer
            command["scale"] = div
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
                if el not in self.config.elements.elements:
                    raise ValueError(f"Element {el} not defined in config.")
        command = {
            "type": "align",
            "elements": elements,
        }
        self._commands.append(command)

    def add_floquet_sequence(
        self,
        phases: list[float],
        delays: list[int],
        repetitions: int | list[int],
        loop_layer: int = -1,
        element: str = None,
        shape: str = None,
    ):
        """
        Adds a Floquet sequence to the experiment. This is a repeating block of
        evenly-spaced, phase-cycled pulses of the form::

            delay[0] — (R(phase[0]) — delay[1]) — (R(phase[1]) — delay[2]) — … repeated N times

        The number of repetitions can be a fixed integer or a 1-D array, in which case
        it becomes the swept loop variable for the given ``loop_layer``.

        Args:
            phases (list[float]): Phase of each pulse in the block, in degrees.
            delays (list[int]): Inter-pulse delays in nanoseconds.  Must contain
                exactly ``len(phases) + 1`` entries (one leading delay plus one after
                each pulse).
            repetitions (int | Iterable): Number of times the pulse block is repeated.
                Pass an array to sweep over this parameter.
            loop_layer (int): Loop layer (1-based) to associate with a swept
                ``repetitions`` array.  Use ``-1`` (default) to auto-assign.
            element (str): Element to apply the sequence to.  Defaults to
                ``settings.res_key`` (the probe channel) when ``None``.
            shape (str): Pulse shape key, defaults to ``settings.pulse_shape``.

        Raises:
            ValueError: If ``len(delays) != len(phases) + 1``.
            ValueError: If ``element`` or ``shape`` are not recognised in the config.
        """

        if len(phases) + 1 != len(delays):
            raise ValueError(
                "There must be one more delay than phase in a Floquet sequence."
            )

        if element is None:
            element = self.probe_key
        elif element not in self.config.elements.elements.keys():
            raise ValueError(f"Element {element} not defined in config.")

        pulse = self.config.elements.elements[element].operations.get(shape, None)
        if shape is None:
            shape = self.pulse_shape
        elif pulse is None:
            raise ValueError(
                f"Pulse shape '{shape}' not recognized in element '{element}'. "
                f"Please provide a valid pulse shape key."
            )

        command = {
            "type": "sequence",
            "shape": shape,
            "element": element,
            "phases": (np.array(phases) / 360) % 1,
            "delays": np.array(delays, dtype=int) // 4,
        }
        if isinstance(repetitions, Iterable):
            layer, div = self._update_loop(np.array(repetitions, dtype=int), loop_layer)
            self._update_loop_type(layer, use_fixed=False)
            command["layer"] = layer
            command["scale"] = div
        else:
            command["repetitions"] = repetitions

        self._commands.append(command)

    def add_z_rotation(
        self,
        angle: float | Iterable,
        elements: str | Iterable[str],
        loop_layer: int = -1,
        phase_cycle: bool = False,
    ):
        """
        Adds a virtual Z rotation to the experiment. This is implemented as a frame rotation in QUA.

        Args:
            angle (float | Iterable): Angle(s) of the Z rotation in degrees.
            elements (str | Iterable[str]): Element(s) to which the Z rotation is applied. Must be defined in the config.
            loop_layer (int): Loop layer (1-based) to associate with a swept
                ``angle`` array.  Use ``-1`` (default) to auto-assign.
            phase_cycle (bool): Whether to vary the angle in the averaging loop for phase cycling. If True, ``angle``
                must be an iterable of angles to cycle through.

        Raises:
            ValueError: If ``elements`` is not defined in the config.
            ValueError: If ``phase_cycle`` is True but ``angle`` is not an iterable of angles.
        """
        if isinstance(elements, str):
            elements = (elements,)
        for element in elements:
            if element not in self.config.elements.elements.keys():
                raise ValueError(f"Element {element} not defined in config.")

        command = {
            "type": "z_rotation",
            "elements": elements,
        }
        if phase_cycle:
            if isinstance(angle, Iterable):
                command["phase_cycle"] = (np.array(angle) / 360) % 1
            else:
                raise ValueError(
                    "Phase cycling requires an iterable of angles, found a scalar instead."
                )
        else:
            if isinstance(angle, Iterable):
                layer, div = self._update_loop((np.array(angle) / 360) % 1, loop_layer)
                self._update_loop_type(layer, use_fixed=True)
                command["layer"] = layer
                command["scale"] = div
            else:
                command["angle"] = (angle / 360) % 1  # convert to fraction of 2pi

        self._commands.append(command)

    def add_frame_change(self, angle: float, elements: str | Iterable[str]):
        """
        Adds frame change compensation to the experiment, which is implemented as a frame rotation after
        each applied pi-half pulse. This feature is useful for correcting out-of-phase overrotation errors
        in pi-half only pulse sequences. In principle, any pulse sequence can be written with only pi-half
        pulses and z-rotations, allowing for frame change compensation to be applied in all cases.

        Args:
            angle (float): Angle of the frame change in degrees.
            elements (str | Iterable[str]): Element(s) to which the frame change is applied. Must be defined in the config.

        Raises:
            ValueError: If ``elements`` is not defined in the config.
        """

        if isinstance(elements, str):
            elements = (elements,)

        for element in elements:
            if element not in self.config.elements.elements.keys():
                raise ValueError(f"Element {element} not defined in config.")

        self.use_frame_change = True
        self.frame_change_angle = (angle / 360) % 1  # convert to fraction of 2pi
        self.frame_change_elements = elements

    def remove_initial_delay(self, remove: bool = True):
        """
        Removes the 5 T1 delay from the start of the sequence. Useful for testing with the
        simulator, but should be generally used to ensure proper thermalization between
        experiments. By default, the delay is included. The delay can be re-added by calling
        this method with `remove` set to False.

        Args:
            remove (bool): By default, is True, removes the initial delay. If False, the delay is re-added.
        """
        self.start_with_wait = not remove

    def _update_loop_type(self, loop_layer, use_fixed):
        """
        Updates the loop type for a given loop layer. This is used to determine whether to use fixed point variables
        for the loop control variables in the QUA program. if no loop layer is specified (loop_layer=-1), this function
        will update the loop type for the first undefined loop layer. If all layers have been identified, it will add a
        new layer with the specified type. It is best to be verbose with loop layers to ensure the correct number are defined.
        An class:`Experiment2D` will insist on a single loop layers for the swept variable, and a class:`Experiment3D`
        similarly insists on two loop layers for the two swept variables.

        For internal use only - will have dramatic mutation side effects otherwise.

        Args:
            loop_layer (int): The layer of the loop to update the type for.
            use_fixed (bool): Whether to use fixed point variables for this loop layer.
        """
        if self.use_fixed_lst[loop_layer - 1] is None:
            self.use_fixed_lst[loop_layer - 1] = use_fixed
        elif self.use_fixed_lst[loop_layer - 1] != use_fixed:
            raise ValueError(
                f"Loop layer {loop_layer} has already been assigned a variable vector with use_fixed={self.use_fixed_lst[loop_layer - 1]}, cannot assign a new variable vector with use_fixed={use_fixed}."
            )

    def _update_loop(self, var_vec, loop_layer):
        """
        Updates the variable vector for the specified loop layer in the experiment.
        This method defines or validates the loop vector that the experiment will iterate over.
        If a variable vector already exists for this loop layer, it verifies consistency by
        checking if the new vector is a constant multiple of the existing one.

        Args:
            var_vec (numpy.ndarray): Array of values for the variable in the experiment.
            loop_layer (int): The loop layer index (1-indexed) to update.
        Returns:
            tuple[int, int | float]: A ``(loop_layer, scale)`` pair where ``loop_layer``
                is the 1-based layer index that was updated and ``scale`` is the
                proportionality constant between the new vector and the one already
                stored (1 if this is the first assignment for this layer).
        Raises:
            ValueError: If the variable vector is all zeros.
            ValueError: If the new vector is not a constant multiple of the existing vector
                in the specified loop layer.
        Warns:
            UserWarning: If the new vector requires division of the existing vector,
                which may introduce runtime delays.
        """
        if np.all(var_vec == 0):
            raise ValueError("Variable vector cannot be all zeros.")

        if loop_layer < 0:
            # Check if a multiple of this var_vec already exists in any layer
            for idx, existing_vec in enumerate(self.var_vec_lst):
                if existing_vec is not None:
                    div = self._list_find_scale_factor(var_vec, existing_vec)
                    if div >= 1:
                        # Reuse the existing layer directly
                        loop_layer = idx + 1
                        return loop_layer, div
                    elif div > 0:
                        # Reuse the existing layer and warn about the division
                        warnings.warn(
                            "New swept variable requires division of an existing variable vector, which may introduce run-time delays."
                        )
                        loop_layer = idx + 1
                        return loop_layer, div

            # If not found, assign to first undefined layer
            for idx, elem in enumerate(self.var_vec_lst):
                if elem is None:
                    self.var_vec_lst[idx] = var_vec
                    loop_layer = idx + 1
                    return loop_layer, 1

            # If all layers defined, add new layer
            self.var_vec_lst.append(var_vec)
            loop_layer = len(self.var_vec_lst) + 1
            return loop_layer, 1

        elif loop_layer > len(self.var_vec_lst):
            # extend with undefined layers until the requested loop layer exists
            self.var_vec_lst.extend([None] * (loop_layer - len(self.var_vec_lst)))
            self.var_vec_lst[loop_layer - 1] = var_vec

        elif self.var_vec_lst[loop_layer - 1] is None:
            # the layer exists but has not been defined yet, so define it
            self.var_vec_lst[loop_layer - 1] = var_vec

        else:
            # the layer exists and has been defined, so check for consistency and return the divisor between the old and new vectors
            div = self._list_find_scale_factor(
                var_vec, self.var_vec_lst[loop_layer - 1]
            )
            if div >= 1 and np.allclose(
                var_vec, div * self.var_vec_lst[loop_layer - 1]
            ):
                return loop_layer, div
            elif div == -1:
                raise ValueError(
                    "New swept variable is a not constant multiple of the exisitng list in this dimension."
                )
            else:
                warnings.warn(
                    "New swept variable requires division, which may introduce run-time delays."
                )
                return loop_layer, div
        return loop_layer, 1

    def _list_find_scale_factor(self, list1, list2):
        """Find the scalar proportionality constant *k* such that ``list1 ≈ k * list2``.

        Returns the constant if the two arrays are parallel (i.e. one is a scalar
        multiple of the other), or ``-1`` if they are not.
        """

        if np.dot(list1, list2) * np.dot(list2, list1) == np.dot(list1, list1) * np.dot(
            list2, list2
        ):
            div = -1
            idx = 0
            while div < 0:
                div = list1[idx] / list2[idx] if list2[idx] != 0 else -1
                idx += 1
            if div > 0:
                if math.isclose(div, round(div)):
                    div = round(
                        div
                    )  # try to save time by using integers in the QUA program when possible
            return div
        else:
            return -1

    def translate_command(
        self,
        n: Any,
        command: dict,
        vars: Any = None,
    ):
        """
        Translates a command dictionary into QUA code.

        Args:
            command (dict): Command dictionary to translate.
            vars (Any, optional): QUA Variables to use for swept parameters.
            loop_idx (Any, optional): QUA Variable to use for loop index.

        Raises:
            ValueError: If the command type is unknown.
        """
        # Resolve the loop variable for this command once, before branching.
        # Each swept command stores a 1-based 'layer' key; vars is a tuple/list
        # of QUA variables indexed by layer-1.
        var = None
        layer = command.get("layer", None)
        scale = command.get("scale", 1)

        if layer is not None and vars is not None:
            if scale == 1:
                var = vars[layer - 1]
            else:
                var = vars[layer - 1] * scale

        if command["type"] == "pulse":

            # Resolve phase: swept (per-field layer) or fixed
            if "phase_layer" in command:
                ph_var = vars[command["phase_layer"] - 1]
                phase = (
                    ph_var * command["phase_scale"]
                    if command["phase_scale"] != 1
                    else ph_var
                )
            elif "phase_cycle" in command:
                pc_var = declare(fixed, value=command["phase_cycle"])
                phase = pc_var[n]
            else:
                phase = command["phase"]

            # Resolve amplitude: swept (per-field layer) or fixed
            if "amplitude_layer" in command:
                amp_var = vars[command["amplitude_layer"] - 1]
                amplitude = (
                    amp_var * command["amplitude_scale"]
                    if command["amplitude_scale"] != 1
                    else amp_var
                )
            else:
                amplitude = command["amplitude"]

            # Resolve length: swept (per-field layer) or fixed
            if "length_layer" in command:
                len_var = vars[command["length_layer"] - 1]
                length = (
                    len_var * command["length_scale"]
                    if command["length_scale"] != 1
                    else len_var
                )
            else:
                length = command["length"]

            frame_rotation_2pi(phase, command["element"])
            play(
                command["shape"] * amp(amplitude),
                command["element"],
                duration=length,
            )
            frame_rotation_2pi(-phase, command["element"])

            if self.use_frame_change:
                frame_rotation_2pi(self.frame_change_angle, *self.frame_change_elements)

        elif command["type"] == "delay":
            duration = command.get("duration", var)
            wait(duration)

        elif command["type"] == "z_rotation":
            if "phase_cycle" in command:
                pc_var = declare(fixed, value=command["phase_cycle"])
                phase = pc_var[n]
            else:
                phase = command.get("phase", var)
            frame_rotation_2pi(phase, *command["elements"])

        elif command["type"] == "align":
            align(*command["elements"]) if command["elements"] is not None else align()

        elif command["type"] == "sequence":
            phases = command.get("phases", None)
            delays = command.get("delays", None)
            repetitions = command.get("repetitions", var)
            shape = command.get("shape", None)
            loop_idx = declare(int, value=0)

            with for_(loop_idx, 0, loop_idx < repetitions, loop_idx + 1):
                wait(delays[0])
                for phase, delay in zip(phases, delays[1:]):
                    frame_rotation_2pi(phase, command["element"])
                    play(
                        shape,
                        command["element"],
                    )
                    frame_rotation_2pi(-phase, command["element"])
                    if self.use_frame_change:
                        frame_rotation_2pi(
                            self.frame_change_angle, *self.frame_change_elements
                        )
                    wait(delay)

        else:
            raise ValueError(f"Unknown command type: {command['type']}")

    def create_experiment(self):
        """
        Creates the Quantum Machine program for the experiment, and returns the
        experiment object as a qua ``program``. This is used by the :meth:`execute_experiment` and
        :meth:`simulate_experiment` methods.

        Returns:
            program: The QUA program for the experiment defined by this class's commands.
        """
        pass  # to be implemented by subclasses

    def validate_experiment(self):
        """
        Function to be implemented by subclasses to validate that the commands and settings for
        the experiment are consistent and valid. Running this function should return helpful error messages
        if the experiment is not properly defined.
        """
        pass  # to be implemented by subclasses

    def compile_to_qua(self, offline: bool = True, save_path: Path = None):
        """
        Compiles the experiment to a QUA program, running all python code in order to generate
        the final QUA program as a string, which is then saved to disk at the specified path. This is useful for
        inspecting the generated QUA program to verify that the commands are being translated as expected, and can be used
        for debugging command translation and config interpreation issues without needing to run the experiment on hardware or in the simulator.

        Args:
            offline (bool): Whether to compile offline, or to use the connected Quantum Machine. Defaults to True for offline compilation.
            save_path (Path): The path to save the compiled QUA program. If None, saves to the same directory
                as this file with the name "compiled_experiment.qua".
        """
        config = self.config.to_opx_config()
        prog = self.create_experiment()
        if offline:
            QuantumMachinesManager.set_capabilities_offline()
        else:
            qm = self.qmm.open_qm(config)

        path = (
            save_path
            if save_path is not None
            else Path(__file__).resolve().parent / "compiled_experiment.qua"
        )
        sourceFile = open(path, "w")
        print(generate_qua_script(prog, config), file=sourceFile)
        sourceFile.close()

    def simulate_experiment(self, sim_length=40_000):
        """
        Simulates the experiment using the configured experiment defined by this class based on the current
        config defined by this instance's ``config`` attribute. The simulation returns the generated waveforms
        of the experiment up to the duration ``sim_length`` in ns. Useful for checking the timings before running
        on hardware.

        Parameters:
            sim_length (int, optional): The duration of the simulation in ns. Defaults to ``40_000``.
        """
        self.validate_experiment()
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
            samples, plot=True, save_path=str(Path(__file__).resolve().parent)
        )
        # return job

    def execute_experiment(
        self, live: bool = True, wait_on_close: bool = True, title_prefix: str = ""
    ):
        """
        Executes the experiment using the configured experiment defined by this class based on the current
        config defined by this instance's `config` attribute. The method handles the execution on hardware,
        data fetching, and basic plotting of results.

        Args:
            live (bool): Passed into `data_processing` to determine whether to display data live during execution
                or only after completion, depending on the subclass implementation.
            wait_on_close (bool): Whether to wait for user to close plot window after experiment completes.
                Only relevant when live=True. Defaults to True.
            title_prefix (str): Prefix to add to plot title for identification. Defaults to empty string.

        Raises:
            ValueError: Throws an error if insufficient details about the experiment are defined.
        """
        if len(self._commands) == 0:
            raise ValueError("No commands have been added to the experiment.")

        expt = self.create_experiment()
        qm = self.qmm.open_qm(self.config.to_opx_config(), close_other_machines=True)
        job = qm.execute(expt)
        self.data_processing(
            qm, job, live=live, wait_on_close=wait_on_close, title_prefix=title_prefix
        )
        qm.close()

    def data_processing(
        self,
        qm: QuantumMachine,
        job: RunningQmJob,
        live: bool = True,
        wait_on_close: bool = True,
        title_prefix: str = "",
    ):
        """
        Grabs the results of the experiment as it is being executed. This method must be
        implemented by subclasses to determine how to fetch and plot the data specific to the experiment.
        The specific handles for the quantum machine and the active job are provided for data fetching. Additionally,
        this method can (and should) update the `save_data_dict` attribute with relevant raw data for saving to
        disk after the experiment completes.

        Subclass implementations should make use of the `live` argument to determine whether to plot data
        live during execution or only after the experiment completes. Autonomous experiments will typically
        want to set `live` to `False` to avoid blocking execution when waiting for user input to close plots.

        Args:
            qm (QuantumMachine): The quantum machine executing the experiment.
            job (RunningQmJob): The job running the experiment.
            live (bool): Whether to display data live during execution or only after completion.
            wait_on_close (bool): Whether to wait for user to close plot after completion. Only relevant when live=True.
            title_prefix (str): Prefix to add to plot titles for identification.
        """
        pass  # to be implemented by subclasses

    def save_data(self, experiment_prefix: str = "experiment"):
        """
        Saves the experiment data to the specified directory using the DataSaver.

        Creates a folder with an auto-incremented name based on ``experiment_prefix``
        (e.g., ``prefix_0001``, ``prefix_0002``) containing:
        - config.json: OPX configuration
        - settings.json: Experiment settings
        - commands.json: List of commands executed
        - data.json: Experimental results and metadata

        Each experiment is saved in a newly created folder with a simple naming structure
        for easy loading elsewhere.

        Args:
            experiment_prefix (str): Prefix for the experiment folder naming. Defaults to "experiment".
                The created folder name will be ``<experiment_prefix>_NNNN`` with a 4-digit counter.

        Raises:
            ValueError: If experiment_prefix contains path separators or is invalid.
        """
        try:
            # Prepare the data payload: include both metadata and results
            data_payload = self.save_data_dict.copy()

            # Save the experiment using DataSaver
            experiment_folder = self.data_saver.save_experiment(
                experiment_prefix=experiment_prefix,
                config=self.config.to_dict(),
                settings=self.settings.to_dict(),
                commands=self._commands,
                data=data_payload,
            )

            print(f"Data saved successfully to folder: {experiment_folder}")
        except Exception as e:
            print(f"Failed to save data: {e}")
