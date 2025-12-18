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
    """
    Class to create and run 2D NMR experiments using the QUA programming language. Inherits
    from the base :class:`Experiment` class and implements methods specific to 2D experiments, which
    can have a broad range of applications such as measuring relaxation times (T1, T2), performing
    pulse amplitude sweeps, and performing two-point correlation measurements under Hamiltonian engineering
    pulse sequences.

    2D experiments involve sweeping one parameter (e.g., pulse amplitude, delay time, evolution time) while
    measuring the system's response. This is typically done by defining a variable vector that contains the values to be
    swept. The experiment loops over this vector, applying the corresponding parameter value in each iteration. In
    this class's implementation, the swept parameter is varied first, then the averaging loop is performed. During longer
    experiments, this ordering should help mitigate the effects of slow drifts in system parameters.
    """

    def __init__(self, settings, config):
        super().__init__(settings=settings, config=config)
        self.sweep_axis = None  # Axis for live plotting and data saving
        self.sweep_label = "Swept Variable"  # Label for sweep axis

    def update_sweep_axis(self, new_axis):
        """
        Updates the sweep axis for live plotting and data saving. If this method is not called, the
        variable vector :attr:`var_vec` will be used as the sweep axis by default. It can be convienient
        to change the sweep axis to a more physically meaningful quantity (e.g., converting pulse amplitude
        rescaling factor physical Vpp units).
        """
        if len(new_axis) != len(self.var_vec):
            raise ValueError(
                "New sweep axis must have the same length as the variable vector."
            )
        self.sweep_axis = new_axis

    def update_sweep_label(self, new_label):
        """
        Updates the label for the sweep axis in live plotting. If this method is not called, the
        default label "Swept Variable" will be used.
        """
        self.sweep_label = new_label

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
        experiment object as a qua ``program()``. This is used by the :meth:`~Experiment.execute_experiment` and
        :meth:`~Experiment.simulate_experiment` methods.

        Returns:
            program: The QUA program for the experiment defined by this class's commands.
        """
        self.validate_experiment()

        with program() as experiment:

            # define the variables and datastreams
            n = declare(int)  # QUA variable for the averaging loop
            m = declare(int)  # QUA variable for floquet loops
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
                        self.translate_command(command, var, m)

                    # wait for ringdown to decay, blank amplifier, set to receive mode
                    safe_mode(switch=self.rx_switch_key, amplifier=self.amplifier_key)
                    wait(self.pre_scan_delay)
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

        fig_live, (ax1, ax2, ax3) = plt.subplots(1, 3, sharex=False, figsize=(16, 6.4))
        interrupt_on_close(fig_live, job)
        try:
            while results.is_processing():
                I, Q, iteration = results.fetch_all()
                axis = self.sweep_axis if self.sweep_axis is not None else self.var_vec
                progress_counter(iteration, self.n_avg, start_time=results.start_time)

                # Convert results into Volts
                I = u.demod2volts(I, self.readout_len)
                Q = u.demod2volts(Q, self.readout_len)

                # 2D color plot: pulse amplitude vs I
                ax1.cla()
                im1 = ax1.pcolormesh(
                    axis,
                    self.tau_sweep / u.us,
                    I.T * 1e6,
                    shading="auto",
                    cmap="viridis",
                )
                ax1.set_ylabel("Delay (µs)")
                ax1.set_xlabel(self.sweep_label)
                ax1.set_title("I")
                if not hasattr(ax1, "_colorbar"):
                    ax1._colorbar = plt.colorbar(im1, ax=ax1, label="I (V)")
                else:
                    ax1._colorbar.update_normal(im1)

                # 2D color plot: pulse amplitude vs tau for Q
                ax2.cla()
                im2 = ax2.pcolormesh(
                    axis,
                    self.tau_sweep / u.us,
                    Q.T * 1e6,
                    shading="auto",
                    cmap="viridis",
                )
                ax2.set_ylabel("Delay (µs)")
                ax2.set_xlabel(self.sweep_label)
                ax2.set_title("Q")
                if not hasattr(ax2, "_colorbar"):
                    ax2._colorbar = plt.colorbar(im2, ax=ax2, label="Q (µV)")
                else:
                    ax2._colorbar.update_normal(im2)

                ax3.cla()
                ax3.plot(axis, I.T[0] * 1e6, label="I")
                ax3.set_xlabel(self.sweep_label)
                ax3.set_ylabel("I (µV)")
                ax3.set_title("Primary signal")
                ax3.legend()

                fig_live.tight_layout()
                fig_live.canvas.draw_idle()
                plt.pause(0.1)

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
        self.save_data_dict.update({"swept_variable": self.var_vec})
        self.save_data_dict.update({"sweep_axis": axis})
        self.save_data_dict.update({"sweep_label": self.sweep_label})
        self.save_data_dict.update({"fig_live": fig_live})

        self.save_data()
