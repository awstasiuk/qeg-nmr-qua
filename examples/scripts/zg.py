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
    pulse_length=2.2 * u.us,
    pulse_amplitude=0.455,  # amplitude is 0.5*Vpp
    rotation_angle=234.7,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=5700 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "test_results",
)

cfg = qnmr.cfg_from_settings(settings)

# write an experiment which measures a basic FID signal
expt = qnmr.Experiment1D(
    config=cfg,
    settings=settings,
)

expt.add_pulse(name=settings.gaussian_pi_half_key, element=settings.res_key)

expt.execute_experiment()

fit = True
if fit:
    
    re = np.array(expt.save_data_dict["I_data"])*1e6
    im = np.array(expt.save_data_dict["Q_data"])*1e6
    ph_ref = np.arctan2(im[0], re[0]) * (180 / np.pi)  # phase reference from first point
    times = np.arange(settings.readout_start, settings.readout_end, settings.dwell_time)
    if abs(ph_ref) > 0.05:
        print(f"Increment phase reference by {ph_ref:.2f} degrees")

    plt.figure(figsize=(10, 5))
    sig = im
    # Calculate the autocorrelation of the signal
    autocorr = acf(sig, nlags=len(sig)-1, fft=True)

    # Plot the autocorrelation
    confidence_95 = 1.96 / np.sqrt(len(sig))
    confidence_99 = 2.58 / np.sqrt(len(sig))

    plt.axhline(y=confidence_95, color='red', linestyle='--', label='95% Confidence Level')
    plt.axhline(y=-confidence_95, color='red', linestyle='--')
    plt.axhline(y=confidence_99, color='black', linestyle='--', label='99% Confidence Level')
    plt.axhline(y=-confidence_99, color='black', linestyle='--')

    plt.stem(times, autocorr, basefmt=" ", markerfmt="o", linefmt="-")
    plt.title(f"Autocorrelation of the Imaginary Component")
    plt.xlabel("Lag (µs)")
    plt.ylabel("Autocorrelation")
    plt.legend()
    plt.grid()
    plt.show()