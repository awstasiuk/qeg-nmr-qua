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
from qualang_tools.loops import from_array
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


class Experiment2D(Experiment):

    def validate_experiment(self):
        """
        Checks to make sure that the experiment contains variable operations,
        since it is a 2D experiment. Variable operations require looping which is
        supported in 2D experiments.

        Raises:
            ValueError: No variable vector was found in the experiment commands.
        """
        if self.var_vec is None:
            raise ValueError(
                "Experiment2D requires variable vectors. Use Experiment1D, or similar, instead."
            )

    def create_experiment(self):
        """
        Creates the Quantum Machine program for the experiment, and returns the
        experiment object as a qua `program`. This is used by the `execute_experiment` and
        `simulate_experiment` methods.

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
            var = declare(fixed)

            if self.start_with_wait:
                wait(self.wait_between_scans, self.probe_key)

            with for_(n, 0, n < self.n_avg, n + 1):  # averaging loop

                with for_(
                    *from_array(var, self.var_vec)
                ):  # inner loop over variable vector
                    drive_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)

                    for command in self._commands:
                        self.translate_command(command, var)

                    # wait for ringdown to decay, blank amplifier, set to receive mode
                    safe_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)
                    wait(self.readout)
                    readout_mode(
                        switch=self.rx_switch_key, amplifier=self.amplifier_key
                    )

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
                    wait(self.wait_between_scans, self.probe_key)

                save(n, n_st)

            with stream_processing():
                n_st.save("iteration")
                I_st.buffer(self.measure_sequence_len).buffer(
                    len(self.var_vec)
                ).average().save("I")
                Q_st.buffer(self.measure_sequence_len).buffer(
                    len(self.var_vec)
                ).average().save("Q")

        return experiment

    def live_data_processing(self, qm, job):
        # Fetching tool
        results = fetching_tool(
            job,
            data_list=["I", "Q", "iteration"],
            mode="live",
        )

        fig_live, (ax1, ax2, ax3) = plt.subplots(1, 3, sharex=False, figsize=(12, 4))
        interrupt_on_close(fig_live, job)
        try:
            while results.is_processing():
                I, Q, iteration = results.fetch_all()
                progress_counter(iteration, self.n_avg, start_time=results.start_time)

                # Convert results into Volts
                I = u.demod2volts(I, self.readout_len)
                Q = u.demod2volts(Q, self.readout_len)

                # 2D color plot: pulse amplitude vs I
                ax1.cla()
                im1 = ax1.pcolormesh(
                    self.var_vec,
                    self.tau_sweep / u.us,
                    I.T * 1e6,
                    shading="auto",
                    cmap="viridis",
                )
                ax1.set_ylabel("Delay (µs)")
                ax1.set_xlabel("Swept Variable")
                ax1.set_title("I")
                if not hasattr(ax1, "_colorbar"):
                    ax1._colorbar = plt.colorbar(im1, ax=ax1, label="I (V)")
                else:
                    ax1._colorbar.update_normal(im1)

                # 2D color plot: pulse amplitude vs tau for Q
                ax2.cla()
                im2 = ax2.pcolormesh(
                    self.var_vec,
                    self.tau_sweep / u.us,
                    Q.T * 1e6,
                    shading="auto",
                    cmap="viridis",
                )
                ax2.set_ylabel("Delay (µs)")
                ax2.set_xlabel("Swept Variable")
                ax2.set_title("Q")
                if not hasattr(ax2, "_colorbar"):
                    ax2._colorbar = plt.colorbar(im2, ax=ax2, label="Q (µV)")
                else:
                    ax2._colorbar.update_normal(im2)

                ax3.cla()
                ax3.plot(self.var_vec, I.T[0] * 1e6, label="I")
                ax3.set_xlabel("Swept Variable")
                ax3.set_ylabel("I (µV)")
                ax3.set_title("Primary signal")
                ax3.legend()

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
