"""
This example shows how to set up and run a 2D over-rotation calibration experiment
using the qeg_nmr_qua package. The experiment determines the frame change angle due
to phase transients in the pulse by applying a phase shifted y-pulse, and storing
the rotation angle error into a symmetry-protected observable before measurement.

The shelving step uses intrinsic interactions to decohere the unwanted signal components,
allowing for higher contrast readout of the desired observable.
"""

import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

u = unit(coerce_to_integer=True)

# create base settings object for experiments
settings = qnmr.ExperimentSettings(
    n_avg=8,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.4083,  # amplitude is 0.5*Vpp
    rotation_angle=255.0,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=2550 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "test_results",
)

cfg = qnmr.cfg_from_settings(settings)

overrot_ang = np.arange(-8,3,1)
expt = qnmr.Experiment2D(settings=settings, config=cfg)

corrected_y = 90-overrot_ang
expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, phase=corrected_y)
expt.add_delay(4*u.us)
expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, phase=180)

#T1 filter
expt.add_delay(1*u.ms)

expt.add_pulse(name=settings.pi_half_key, element=settings.res_key)

expt.update_sweep_axis(overrot_ang)
expt.update_sweep_label("Over-rotation Angle (deg)")

expt.execute_experiment()

fit = True
if fit:
    fig, ax = plt.subplots()
    re = np.array(expt.save_data_dict["I_data"])
    sig = re[:,0]
    ang = np.array(expt.save_data_dict["sweep_axis"])
    ax.scatter(ang, sig, label="Data Points")

    # Fit to a linear curve
    coeffs = np.polyfit(ang, sig, 1)
    fit_line = np.polyval(coeffs, ang)
    ax.plot(ang, fit_line, "--", label="Linear Fit")

    # Calculate and indicate the zero crossing
    zero_crossing = -coeffs[1] / coeffs[0]
    ax.axvline(zero_crossing, color="red", linestyle="--", label=f"Zero Crossing: {zero_crossing:.2f} deg")
    ax.legend()

    ax.set_xlabel("Over-rotation Angle (deg)")
    ax.set_ylabel("Error Signal")
    ax.set_title("Over-rotation Calibration")
    plt.show()