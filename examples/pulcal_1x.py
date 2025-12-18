"""
This example shows how to set up and run a 2D pulse calibration experiment
using the qeg_nmr_qua package. The experiment applies a series of pulses with
varying amplitudes to the nuclear spin system and measures the resulting FID signals, in an
effort to calibrate the pulse amplitude for a pi/2 rotation.


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
    pulse_amplitude=0.4087,  # amplitude is 0.5*Vpp
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

amp_list = np.arange(.9,1.11,.025)
expt = qnmr.Experiment2D(settings=settings, config=cfg)

n_wraps = 1

for i in range(n_wraps * 4):
    expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, amplitude=amp_list)
    expt.add_delay(2*u.us)

expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, amplitude=amp_list)

expt.update_sweep_axis(amp_list*settings.pulse_amplitude)
expt.update_sweep_label("Pulse Amplitude (Vpp)")
expt.execute_experiment()

fit = True
if fit:
    results = expt.save_data_dict["data"]
    re = np.array(results["I_data"])*1e6
    power = np.array(results["sweep_axis"])

    plt.scatter(power,re[:,0])
    coefficients = np.polyfit(power, re[:, 0], 2)
    parabola = np.poly1d(coefficients)

    vertex_x = -coefficients[1] / (2 * coefficients[0])
    vertex_y = parabola(vertex_x)

    x_fit = np.linspace(power.min(), power.max(), 500)
    y_fit = parabola(x_fit)
    plt.plot(x_fit, y_fit, color='red', label='Fitted Parabola')

    plt.scatter(vertex_x, vertex_y, color='green', label='Max Pwr={:.3f} Vpp'.format(vertex_x))
    plt.legend()
    plt.xlabel('Pulse Amplitude (Vpp)')
    plt.ylabel('FID Signal Amplitude (µV)')
    plt.title('Pulse Calibration: FID Signal vs Pulse Amplitude, {} wraps'.format(n_wraps))
    print(f"Maximum at x = {vertex_x}, y = {vertex_y}")