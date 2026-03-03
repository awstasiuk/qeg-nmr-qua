import warnings
import matplotlib.pyplot as plt

from qeg_nmr_qua.experiment.macros import (
    readout_mode,
    safe_mode,
    drive_mode,
)
from qeg_nmr_qua.experiment.experiment import Experiment
from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.config.settings import ExperimentSettings

from qualang_tools.results import fetching_tool, progress_counter
from qualang_tools.plot import interrupt_on_close
from qualang_tools.units import unit
from qualang_tools.loops import from_array
from qm import QuantumMachine
from qm.jobs.running_qm_job import RunningQmJob
from qm.qua import (
    wait,
    measure,
    save,
    program,
    declare,
    reset_frame,
    stream_processing,
    declare_stream,
    for_,
    if_,
    fixed,
    demod,
)

u = unit(coerce_to_integer=True)


class Experiment3D(Experiment):
    """
    Class to create and run 3D NMR experiments using the QUA programming language. Inherits
    from the base :class:`Experiment` class and implements methods specific to 3D experiments, which
    can have a broad range of applications such as measuring relaxation times (T1, T2), performing
    pulse amplitude sweeps, and performing two-point correlation measurements under Hamiltonian engineering
    pulse sequences.

    3D experiments involve sweeping two parameters (e.g., pulse amplitude, delay time, evolution time) while
    measuring the system's response. This is typically done by defining two variable vectors that contain the values to be
    swept. The experiment loops over these vectors, applying the corresponding parameter values in each iteration. In
    this class's implementation, the swept parameters are varied first, then the averaging loop is performed. During longer
    experiments, this ordering should help mitigate the effects of slow drifts in system parameters.
    """

    def __init__(
        self,
        settings: ExperimentSettings,
        config: OPXConfig = None,
        connect: bool = True,
    ):
        super().__init__(settings=settings, config=config, connect=connect)
        self.sweep_axis_inner = None  # Inner Axis for live plotting and data saving
        self.sweep_label_inner = "Inner Swept Variable"  # Label for sweep axis
        self.sweep_axis_outer = None  # Outer Axis for live plotting and data saving
        self.sweep_label_outer = "Outer Swept Variable"  # Label for sweep axis
        self.use_fixed_lst = [None, None]  # whether to use fixed point for looping
        self.var_vec_lst = [None, None]  # variable vector for looped experiments

    def update_sweep_axis_inner(self, new_axis):
        """
        Updates the sweep axis for live plotting and data saving. If this method is not called, the
        variable vector :attr:`var_vec` will be used as the sweep axis by default. It can be convenient
        to change the sweep axis to a more physically meaningful quantity (e.g., converting pulse amplitude
        rescaling factor physical Vpp units).
        """
        if len(new_axis) != len(self.var_vec_lst[1]):
            raise ValueError(
                "New sweep axis must have the same length as the inner variable vector."
            )
        self.sweep_axis_inner = new_axis

    def update_sweep_label_inner(self, new_label: str):
        """
        Updates the label for the sweep axis in live plotting. If this method is not called, the
        default label "Swept Variable" will be used.
        """
        self.sweep_label_inner = new_label

    def update_sweep_axis_outer(self, new_axis):
        """
        Updates the sweep axis for live plotting and data saving. If this method is not called, the
        variable vector :attr:`var_vec` will be used as the sweep axis by default. It can be convenient
        to change the sweep axis to a more physically meaningful quantity (e.g., converting pulse amplitude
        rescaling factor physical Vpp units).
        """
        if len(new_axis) != len(self.var_vec_lst[0]):
            raise ValueError(
                "New sweep axis must have the same length as the outer variable vector."
            )
        self.sweep_axis_outer = new_axis

    def update_sweep_label_outer(self, new_label):
        """
        Updates the label for the sweep axis in live plotting. If this method is not called, the
        default label "Swept Variable" will be used.
        """
        self.sweep_label_outer = new_label

    def validate_experiment(self):
        """
        Checks to make sure that the experiment contains variable operations,
        since it is a 3D experiment. Variable operations require looping which is
        supported in 3D experiments.

        Raises:
            ValueError: No variable vector was found in the experiment commands.
        """
        if self.var_vec_lst[1] is None and self.var_vec_lst[0] is None:
            raise ValueError(
                "Experiment3D requires two swept parameters. Use Experiment1D, or similar, instead."
            )
        elif self.var_vec_lst[1] is None or self.var_vec_lst[0] is None:
            raise ValueError(
                "Experiment3D requires two swept parameters. To sweep a single parameter, use Experiment2D, or similar, instead."
            )

        if len(self.var_vec_lst) > 2:
            warnings.warn(
                "Experiment3D only supports two variable vectors, but more were found."
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
            loop_idx = declare(int)  # QUA variable for floquet loops
            n_st = declare_stream()  # Stream for the averaging iteration 'n'
            I1 = declare(fixed)
            Q1 = declare(fixed)
            I2 = declare(fixed)
            Q2 = declare(fixed)
            I_st = declare_stream()
            Q_st = declare_stream()
            t1 = declare(int)
            t2 = declare(int)

            if self.use_fixed_lst[0]:
                var_outer = declare(fixed)
            else:
                var_outer = declare(int)

            if self.use_fixed_lst[1]:
                var_inner = declare(fixed)
            else:
                var_inner = declare(int)

            if self.start_with_wait:
                wait(self.wait_between_scans, self.probe_key)

            with for_(n, 0, n < self.n_avg, n + 1):  # averaging loop, "layer 0"
                with if_(n > 0):
                    wait(self.wait_between_scans, self.probe_key)
                with for_(
                    *from_array(var_outer, self.var_vec_lst[0])
                ):  # outer loop over variable vector, layer 1

                    with for_(
                        *from_array(var_inner, self.var_vec_lst[1])
                    ):  # inner loop over variable vector, layer 2

                        drive_mode(
                            switch=self.rx_switch_key, amplifier=self.amplifier_key
                        )

                        for command in self._commands:
                            self.translate_command(
                                command, (var_outer, var_inner), loop_idx
                            )

                        # wait for ringdown to decay, blank amplifier, set to receive mode
                        safe_mode(
                            switch=self.rx_switch_key, amplifier=self.amplifier_key
                        )
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
                        safe_mode(
                            switch=self.rx_switch_key, amplifier=self.amplifier_key
                        )
                        reset_frame(self.probe_key, self.helper_key)

                save(n, n_st)

            with stream_processing():
                n_st.save("iteration")
                I_st.buffer(self.measure_sequence_len).buffer(
                    len(self.var_vec_lst[1])
                ).buffer(len(self.var_vec_lst[0])).average().save("I")
                Q_st.buffer(self.measure_sequence_len).buffer(
                    len(self.var_vec_lst[1])
                ).buffer(len(self.var_vec_lst[0])).average().save("Q")

        return experiment

    def data_processing(
        self,
        qm: QuantumMachine,
        job: RunningQmJob,
        live: bool,
        wait_on_close: bool = True,
        title_prefix: str = "",
    ):
        """
        Handles live data processing for a 3D experiment during execution.

        Fetched data has shape ``(n_outer, n_inner, n_time)`` after on-FPGA averaging.
        Two heatmaps are displayed, both with the outer-sweep variable on the y-axis
        and the inner-sweep variable on the x-axis:

        * **Left panel** — ``I[:, :, 0]``: the first sampled time-point of the I
          quadrature for every (outer, inner) parameter pair, in µV.  This is the
          primary NMR observable for sequences that refocus at time zero.
        * **Right panel** — ``std`` of ``Q[:, :, -20:]``: the standard deviation computed
          over the final 20 readout points of the Q quadrature, in µV.  This tracks the
          noise floor of the tail of the FID.

        Args:
            qm (QuantumMachine): The Quantum Machine instance used to run the experiment.
            job (RunningQmJob): The job object representing the running experiment.
            live (bool): Flag indicating whether to generate live plots during data acquisition.
            wait_on_close (bool): Whether to wait for user to close plot after completion.
            title_prefix (str): Prefix to add to plot title.
        """
        import numpy as np

        results = fetching_tool(
            job,
            data_list=["I", "Q", "iteration"],
            mode="live",
        )

        # Resolve the physical axes to display (fall back to raw loop vectors)
        axis_outer = (
            self.sweep_axis_outer
            if self.sweep_axis_outer is not None
            else self.var_vec_lst[0]
        )
        axis_inner = (
            self.sweep_axis_inner
            if self.sweep_axis_inner is not None
            else self.var_vec_lst[1]
        )

        if live:
            fig_live, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
            if wait_on_close:
                interrupt_on_close(fig_live, job)

        I = None
        Q = None

        try:
            while results.is_processing():
                I, Q, iteration = results.fetch_all()

                progress_counter(iteration, self.n_avg, start_time=results.start_time)

                # Convert demodulated counts → Volts; shape (n_outer, n_inner, n_time)
                I = u.demod2volts(I, self.readout_len)
                Q = u.demod2volts(Q, self.readout_len)

                if live and I.ndim == 3 and I.shape[2] >= 1:
                    # --- Panel 1: first I time-point heatmap ---
                    I_first = I[:, :, 0] * 1e6  # (n_outer, n_inner), µV

                    # --- Panel 2: std  of last 20 Q time-points ---
                    n_tail = min(20, I.shape[2])
                    Q_tail = Q[:, :, -n_tail:] * 1e6  # µV
                    Q_metric = np.std(Q_tail, axis=2)

                    if title_prefix:
                        fig_live.suptitle(title_prefix, fontsize=12, fontweight="bold")

                    ax1.cla()
                    im1 = ax1.pcolormesh(
                        axis_inner,
                        axis_outer,
                        I_first,
                        shading="auto",
                        cmap="viridis",
                    )
                    ax1.set_xlabel(self.sweep_label_inner)
                    ax1.set_ylabel(self.sweep_label_outer)
                    ax1.set_title("I  (first point, µV)")
                    if not hasattr(ax1, "_colorbar"):
                        ax1._colorbar = plt.colorbar(im1, ax=ax1, label="I (µV)")
                    else:
                        ax1._colorbar.update_normal(im1)

                    ax2.cla()
                    im2 = ax2.pcolormesh(
                        axis_inner,
                        axis_outer,
                        Q_metric,
                        shading="auto",
                        cmap="plasma",
                    )
                    ax2.set_xlabel(self.sweep_label_inner)
                    ax2.set_ylabel(self.sweep_label_outer)
                    ax2.set_title("Q tail noise (20pt std dev) [µV]")
                    if not hasattr(ax2, "_colorbar"):
                        ax2._colorbar = plt.colorbar(im2, ax=ax2, label="(µV)")
                    else:
                        ax2._colorbar.update_normal(im2)

                    fig_live.tight_layout()
                    fig_live.canvas.draw_idle()
                    plt.pause(0.1)

        except KeyboardInterrupt:
            print("Experiment interrupted by user.")

        if live and wait_on_close:
            message = "Acquisition finished. Close the plot window to continue."
            print(message)
            try:
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

        if live and not wait_on_close:
            plt.close(fig_live)
            fig_live = None

        self.save_data_dict.update({"I_data": I})
        self.save_data_dict.update({"Q_data": Q})
        self.save_data_dict.update({"var_vec_outer": self.var_vec_lst[0]})
        self.save_data_dict.update({"var_vec_inner": self.var_vec_lst[1]})
        self.save_data_dict.update({"sweep_axis_outer": axis_outer})
        self.save_data_dict.update({"sweep_axis_inner": axis_inner})
        self.save_data_dict.update({"sweep_label_outer": self.sweep_label_outer})
        self.save_data_dict.update({"sweep_label_inner": self.sweep_label_inner})
        self.save_data_dict.update({"fig_live": fig_live})

        self.save_data()
