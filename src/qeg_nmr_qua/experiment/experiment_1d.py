from qeg_nmr_qua.experiment.macros import (
    readout_mode,
    safe_mode,
    drive_mode,
)
from qeg_nmr_qua.experiment.experiment import Experiment

import matplotlib.pyplot as plt
from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.plot import interrupt_on_close
from qualang_tools.units import unit
from qm.qua import (
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


class Experiment1D(Experiment):
    """
    Class to create and run 1D NMR experiments using the QUA programming language. Inherits
    from the base :class:`Experiment` class and implements methods specific to 1D experiments, usually
    used for measuring free induction decay (FID) signals. The resulting signal is used to
    calibrate drifts in the nuclear spin frequency phase reference.

    In solid-state systems, the FID signal typically decays within 100-500 microseconds due to
    strong dipolar interactions between nuclear spins. Direct fitting of T2* from the FID is often
    unreliable because of this rapid decay.
    """

    def validate_experiment(self):
        """
        Checks to make sure that the experiment contains no variable operations,
        since it is a 1D experiment. Variable operations require looping which is not
        supported in 1D experiments.

        Raises:
            ValueError: A looping operation was found in the experiment commands.
        """
        if self.var_vec is not None:
            raise ValueError(
                "Experiment1D does not support variable vectors. Use Experiment2D, or similar, instead."
            )

    def create_experiment(self):
        """
        Creates the Quantum Machine program for the experiment, and returns the
        experiment object as a qua ``program``. This is used by the :meth:`~Experiment.execute_experiment` and
        :meth:`~Experiment.simulate_experiment` methods.

        Returns:
            program: The QUA program for the experiment defined by this class's commands.
        """

        self.validate_experiment()

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

            if self.start_with_wait:
                wait(self.wait_between_scans)

            with for_(n, 0, n < self.n_avg, n + 1):  # averaging loop
                drive_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)

                for command in self._commands:
                    self.translate_command(command)

                # wait for ringdown to decay, blank amplifier, set to receive mode
                safe_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)
                wait(self.pre_scan_delay)
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

                # set to safe mode and allow system to relax
                safe_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)
                save(n, n_st)
                wait(self.wait_between_scans, self.probe_key)

            with stream_processing():
                n_st.save("iteration")
                I_st.buffer(self.measure_sequence_len).average().save("I")
                Q_st.buffer(self.measure_sequence_len).average().save("Q")

        return experiment

    def live_data_processing(self, qm, job):
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

        # Keep the interactive plot open after acquisition until the user closes it
        message = "Acquisition finished. Close the plot window to continue."
        print(message)
        try:
            # Add a centered text box on the figure (figure coordinates)
            fig_live.text(
                0.04,
                0.02,
                message,
                ha="left",
                va="bottom",
                fontsize=8,
                bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"),
            )
            fig_live.canvas.draw_idle()
        except Exception as e:
            print(e)
        while plt.fignum_exists(fig_live.number):
            plt.pause(0.5)

        self.save_data_dict.update({"I_data": I})
        self.save_data_dict.update({"Q_data": Q})
        self.save_data_dict.update({"fig_live": fig_live})

        self.save_data()
