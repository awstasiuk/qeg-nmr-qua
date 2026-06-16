"""
Resonator spectroscopy. Measures the response of a resonator over a range of frequencies
using a continuous wave excitation (wobbler). The response is measured in terms of the
I and Q quadratures of the transmitted signal through the probe. The results are plotted
in real-time as the experiment runs, and saved to disk upon completion.

The probe tuning must be varied manually while this script is running to find the optimal
frequency for the resonator. The center frequency, plotted as a dashed line at 0 Hz offset,
should be aligned with the minimum of the resonator response curve. The depth and location of
the minimum of the response curve is varied by the probe's tuning and matching knobs.

WARNING: Ensure that the amplifier is turned OFF before running this script to prevent
damage to the hardware. This script includes a user confirmation step to verify that the
amplifier is off before proceeding with the experiment.
"""

import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

from qm.qua import *
from qm import QuantumMachinesManager, generate_qua_script
from qualang_tools.loops import from_array
from qualang_tools.results import fetching_tool
from qualang_tools.plot import interrupt_on_close

from qeg_nmr_qua.config.settings import ExperimentSettings
from qeg_nmr_qua.config.config_from_settings import cfg_from_settings
from qeg_nmr_qua.analysis.data_saver import DataSaver
from qeg_nmr_qua.experiment.macros import readout_mode

from qualang_tools.units import unit

u = unit(coerce_to_integer=True)

plt.ion()

settings = ExperimentSettings(
    n_avg=4,
    pulse_length=1.24 * u.us,
    pulse_amplitude=0.475,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=118.7,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=15830 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "test_results",
)
cfg = cfg_from_settings(settings)
config = cfg.to_opx_config()

# ---- Program parameters ---- #
avg_bit_shift = 2
n_avg = 2**avg_bit_shift
res_key = settings.res_key
amp_key = settings.amp_key
sw_key = settings.sw_key
res_relaxation = settings.resonator_relaxation // 4  # From ns to clock cycles


# ---- Resonator spectroscopy parameters ---- #
res_frequency = settings.center_freq - settings.offset_freq
res_spec_span = 2000 * u.kHz
res_spec_df = 10 * u.kHz
res_spec_sweep_dfs = np.arange(-res_spec_span, res_spec_span + res_spec_df, res_spec_df)
res_spec_frequency = res_spec_sweep_dfs + res_frequency

window_max = 80  # expected max signal with default settings in microvolts

# ---- Data to save ---- #
save_data_dict = {
    "n_avg": n_avg,
    "resonator_frequency": res_spec_frequency,
    "config": config,
}

# ---- Resonator spectroscopy QUA program ---- #
with program() as prog:
    readout_mode(switch=sw_key, amplifier=amp_key)
    n = declare(int)  # QUA variable for the averaging loop
    df = declare(int)  # QUA variable for the sweep of the readout IF frequency
    I = declare(fixed)  # QUA variable for the measured 'I' quadrature
    Q = declare(fixed)  # QUA variable for the measured 'Q' quadrature
    I_st = declare_stream()  # Stream for the 'I' quadrature
    Q_st = declare_stream()  # Stream for the 'Q' quadrature
    I_avg = declare(fixed)
    Q_avg = declare(fixed)

    with infinite_loop_():
        with for_(*from_array(df, res_spec_sweep_dfs)):
            update_frequency(
                res_key, df + res_frequency
            )  # Update the frequency of the digital oscillator linked to the resonator element
            assign(I_avg, 0.0)
            assign(Q_avg, 0.0)
            with for_(n, 0, n < n_avg, n + 1):
                measure(
                    "readout",
                    res_key,
                    demod.full("cos", I, "out1"),
                    demod.full("sin", Q, "out1")
                )
                assign(I_avg, I_avg + I >> avg_bit_shift)
                assign(Q_avg, Q_avg + Q >> avg_bit_shift)
                # Save the 'I' & 'Q' quadratures to their respective streams
                # Wait for the resonator to deplete
                wait(res_relaxation, res_key)
            save(I_avg, I_st)
            save(Q_avg, Q_st)

    with stream_processing():
        I_st.buffer(len(res_spec_sweep_dfs)).save("I")
        Q_st.buffer(len(res_spec_sweep_dfs)).save("Q")

# ---- Open communication with the OPX ---- #
qmm = QuantumMachinesManager(host=cfg.qop_ip, cluster_name=cfg.cluster)

# ---- User safety verification ---- #
verified = False
response = (
    input("Is the amplifier turned OFF? Type 'YES' to continue: ").strip().upper()
)
if response == "YES":
    confirmation = input("Are you sure? Type 'YES' to confirm: ").strip().upper()
    if confirmation == "YES":
        verified = True
    else:
        print("Spectroscopy experiment cancelled.")
else:
    print("Spectroscopy experiment cancelled.")

if verified:
    # Open the quantum machine
    qm = qmm.open_qm(config, close_other_machines=True)
    # Send the QUA program to the OPX, which compiles and executes it
    job = qm.execute(prog)
    # Creates a result handle to fetch data from the OPX
    res_handles = fetching_tool(job, data_list=["I", "Q"], mode="live")
    # Waits (blocks the Python console) until all results have been acquired
    fig_live, ax1 = plt.subplots(1, 1, sharex=True)
    interrupt_on_close(fig_live, job)  # Interrupts the job when closing the figure
    try:
        while res_handles.is_processing():
            # Fetch results
            I, Q = res_handles.fetch_all()
            # Convert results into Volts
            I = u.demod2volts(I, settings.dwell_time) * 1e6
            Q = u.demod2volts(Q, settings.dwell_time) * 1e6
            S = I + 1j * Q
            R = np.abs(S)   # Amplitude
            width = 10
            smooth_R = np.convolve(
                R, np.ones(width) / width, mode="same"
            )  # Centered simple moving average
            phase = np.angle(S)  # Phase
            # Plot results (update axes)
            fig_live.suptitle("Resonator spectroscopy")
            ax1.cla()
            ax1.plot(
                (res_spec_sweep_dfs) / u.kHz,
                R,
                label=f"Resonator {res_key} at {res_frequency/u.MHz:.3f} MHz",
            )
            ax1.plot(
                (res_spec_sweep_dfs) / u.kHz,
                smooth_R,
                label=f"Resonator {res_key} at {res_frequency/u.MHz:.3f} MHz (smoothed)",
            )
            ax1.vlines(
                [0],
                ymin=0,
                ymax=np.max(R),
                color="k",
                linestyle="--",
                label="Center freq",
            )
            ax1.set_ylabel(r"$R=\sqrt{I^2 + Q^2}$ (µV)")
            ax1.set_xlabel(r"$\Delta f$ from Drive Freq. (kHz)")
            ax1.set_ylim([0, window_max])

            fig_live.tight_layout()
            fig_live.canvas.draw_idle()
            plt.pause(0.1)
    except KeyboardInterrupt:
        print("Interrupted by user.")

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

    # Save results
    save_dir = (
        Path(__file__).resolve().parent / "wobb_data"
        if settings.save_dir is None
        else settings.save_dir
    )
    saver = DataSaver(save_dir)
    save_data_dict.update({"I_data": I})
    save_data_dict.update({"Q_data": Q})
    save_data_dict.update({"fig_live": fig_live})

    qm.close()
