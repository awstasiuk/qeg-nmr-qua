# src/qeg_nmr_qua/experiment/experiment.py
from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.experiment.macros import readout_mode, safe_mode, drive_mode

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
)

u = unit(coerce_to_integer=True)


class Experiment1D:
    def __init__(self, config: OPXConfig = None):
        """
        Initializes the base experiment class with default configurations and containers for commands, results,
        plotting data, and experimental delays. This class serves as a foundational structure for conducting
        experiments.
        Args:
            config (, optional): A configuration object for the experiment. If not provided, a default
                                         `OPXConfig` object is created.

        """
        self.config = config if config is not None else OPXConfig()

        self.n_avg = 4
        self.pi_half_pulse = "pi_half"

        self.probe_key = "resonator"
        self.helper_key = "helper"
        self.amplifier_key = "amplifier"
        self.rx_switch_key = "switch"

        readout_len = self.config.pulses.pulses["readout_pulse"].length
        tau_min = 0 * u.us
        tau_max = 256 * u.us
        measure_sequence_len = (tau_max - tau_min) // readout_len
        self.tau_sweep = np.arange(
            0.5 * readout_len, (measure_sequence_len + 0.5) * readout_len, readout_len
        )
        self.loop_wait_cycles = readout_len // 4

        self.thermal_reset = 4 * u.s  # 5 T1

        self.qmm = QuantumMachinesManager(
            self.config.qop_ip, cluster_name=self.config.cluster
        )
        # ---- Data to save ---- #
        self.save_data_dict = {
            "n_avg": self.n_avg,
            "config": config,
        }
        self.save_dir = Path(__file__).resolve().parent / "data"

    def create_experiment(self):
        """
        Creates the Quantum Machine program for the experiment, and returns the
        experiment object as a qua `program`. This is used by the `execute_experiment` and
        `simulate_experiment` methods.

        Returns:
            program: The QUA program for the experiment defined by this class's commands.
        """

        with program() as experiment:

            # define the variables and datastreams
            n = declare(int)  # QUA variable for the averaging loop
            n_st = declare_stream()  # Stream for the averaging iteration 'n'
            I1 = declare(fixed)
            Q1 = declare(fixed)
            I2 = declare(fixed)
            Q2 = declare(fixed)
            I_st = declare_stream()
            Q_st = declare_stream()
            t1 = declare(int)
            t2 = declare(int)

            with for_(n, 0, n < self.n_avg, n + 1):  # averaging loop
                # final measurement excitation pulse
                play(self.pi_half_pulse, self.probe_key)

                # wait for ringdown to decay, blank amplifier, set to receive mode
                safe_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)
                wait(self.readout)
                readout_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)

                # measure the FID signal via resonator and helper elements
                with for_(t1, 0, t1 < self.measure_sequence_len, t1 + 2):
                    measure(
                        "no_pulse_readout",
                        self.probe_key,
                        demod.full("rotated_cos", I1, "out1"),
                        demod.full("rotated_sin", Q1, "out1"),
                    )
                    save(I1, I_st)
                    save(Q1, Q_st)
                    wait(self.loop_wait_cycles, self.probe_key)
                wait(
                    self.loop_wait_cycles, self.helper_key
                )  # Delay the second measurement loop
                with for_(t2, 1, t2 < self.measure_sequence_len, t2 + 2):
                    measure(
                        "no_pulse_readout",
                        self.helper_key,
                        demod.full("rotated_cos", I2, "out1"),
                        demod.full("rotated_sin", Q2, "out1"),
                    )
                    save(I2, I_st)
                    save(Q2, Q_st)
                    wait(self.loop_wait_cycles, self.helper_key)
                safe_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)
                wait(self.spin_relax, self.res_key)
                save(n, n_st)

            with stream_processing():
                n_st.save("iteration")
                I_st.buffer(self.measure_sequence_len).average().save("I")
                Q_st.buffer(self.measure_sequence_len).average().save("Q")

        return experiment

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
        if len(self.commands) == 0:
            raise ValueError("No commands have been added to the experiment.")
        if self.var_vec is None:
            raise ValueError("No inner loop has been defined, invalid sweep.")

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
        if len(self.commands) == 0:
            raise ValueError("No commands have been added to the experiment.")
        if self.var_vec is None:
            raise ValueError("No inner loop has been defined, invalid sweep.")

        expt = self.create_experiment()
        qm = self.qmm.open_qm(self.config.to_opx_config(), close_other_machines=True)
        job = qm.execute(expt)

        # Fetching tool
        results = fetching_tool(
            job,
            data_list=["I", "Q", "iteration"],
            mode="live",
        )

        fig_live, (ax1, ax2) = plt.subplots(2, 1, sharex=True, height_ratios=[0, 1])
        ax1.set_visible(False)
        interrupt_on_close(fig_live, job)
        try:
            while results.is_processing():
                I, Q, iteration = results.fetch_all()
                progress_counter(iteration, self.n_avg, start_time=results.start_time)

                # Convert results into Volts
                I = u.demod2volts(I, self.readout_len)
                Q = u.demod2volts(Q, self.readout_len)

                ax2.cla()
                fig_live.suptitle(f"Good title, scan {iteration+1}/{self.n_avg}")
                ax2.plot(
                    (self.tau_sweep) / u.us,
                    I * 1e6,
                    label=f"I Resonator {self.probe_key}",
                )
                ax2.plot(
                    (self.tau_sweep) / u.us,
                    Q * 1e6,
                    label=f"Q Resonator {self.probe_key}",
                )
                ax2.set_ylabel("I&Q (µV)")
                ax2.set_xlabel("Acquisition time (µs)")
                ax2.legend()
                fig_live.tight_layout()
                fig_live.canvas.draw_idle()
                plt.pause(0.25)

        except KeyboardInterrupt:
            print("Experiment interrupted by user.")

        print("Experiment finished.")

        # Save results
        script_name = Path(__file__).name
        data_handler = DataHandler(root_data_folder=self.save_dir)
        self.save_data_dict.update({"I_data": I})
        self.save_data_dict.update({"Q_data": Q})
        self.save_data_dict.update({"fig_live": fig_live})
        # data_handler.additional_files = {script_name: script_name, **default_additional_files} ???

        data_handler.save_data(
            data=self.save_data_dict,
            name="_".join(script_name.split("_")[1:]).split(".")[0],
        )
        print(f"Data saved in: {data_handler.data_folder}")
        qm.close()
