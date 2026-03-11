"""
This example shows how to set up and run a simple free induction decay (FID)
experiment using the qeg_nmr_qua package. The experiment applies a single
π/2 pulse to the nuclear spin system and measures the resulting FID signal.

This reproduces the "zero-go" function often used in Brucker systems.
"""

import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import acf

u = unit(coerce_to_integer=True)

# create base settings object for experiments
settings = qnmr.ExperimentSettings(
    n_avg=4,
    pulse_length=1.12 * u.us,
    pulse_amplitude=0.48,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=249.3,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=9800 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path.home() / "Dropbox/QEG/NMR/RawData" / Path(__file__).stem
)

cfg = qnmr.cfg_from_settings(settings)

# write an experiment which measures a basic FID signal
expt = qnmr.Experiment1D(
    config=cfg,
    settings=settings,
)

fc_elements = (settings.res_key, settings.helper_key)
expt.add_frame_change(angle=-4.0, elements=fc_elements)

expt.add_pulse(element=settings.res_key)

expt.execute_experiment()

# expt.remove_initial_delay()
# expt.simulate_experiment()

fit = True
if fit:
    data_dict = expt.save_data_dict
    re = np.array(data_dict["I_data"]) * 1e6
    im = np.array(data_dict["Q_data"]) * 1e6
    ph_ref = np.arctan2(im[0], re[0]) * (180 / np.pi)
    times = np.arange(settings.readout_start,
                      settings.readout_end,
                      settings.dwell_time) / u.us # convert to us for plotting

    if abs(ph_ref) > 0.1:
        print(f"Increment phase reference by {ph_ref:.2f} degrees to {(settings.rotation_angle+ph_ref):.2f}" )

    sig = im

    # --- Autocorrelation ---
    autocorr = acf(sig, nlags=len(sig)-1, fft=True)

    # --- Fourier transform of autocorrelation ---
    fft_vals = np.fft.fft(autocorr)
    dt = settings.dwell_time
    freqs = np.fft.fftfreq(len(autocorr), d=dt / u.ms) # convert to kHz (1/ms)

    # Shift zero frequency to center
    fft_vals_shifted = np.fft.fftshift(fft_vals)
    freqs_shifted = np.fft.fftshift(freqs)

    # --- Plotting ---
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))

    # Confidence bounds
    confidence_95 = 1.96 / np.sqrt(len(sig))
    confidence_99 = 2.58 / np.sqrt(len(sig))

    # Autocorrelation plot
    axs[0].axhline(y=confidence_95, color='red', linestyle='--', label='95% Confidence Level')
    axs[0].axhline(y=-confidence_95, color='red', linestyle='--')
    axs[0].axhline(y=confidence_99, color='black', linestyle='--', label='99% Confidence Level')
    axs[0].axhline(y=-confidence_99, color='black', linestyle='--')

    axs[0].stem(times[:len(autocorr)], autocorr, basefmt=" ", markerfmt="o", linefmt="-")
    axs[0].set_title("Autocorrelation of the Imaginary Component")
    axs[0].set_xlabel("Lag (µs)")
    axs[0].set_ylabel("Autocorrelation")
    axs[0].legend()
    axs[0].grid()

    # Fourier transform plot (Power Spectral Density)
    axs[1].plot(freqs_shifted, np.abs(fft_vals_shifted))
    axs[1].set_title("Fourier Transform of Autocorrelation (PSD)")
    axs[1].set_xlim(0, np.max(freqs_shifted))
    axs[1].set_xlabel("Frequency (kHz)")
    axs[1].set_ylabel("Magnitude")
    axs[1].grid()

    plt.tight_layout()
    plt.show()