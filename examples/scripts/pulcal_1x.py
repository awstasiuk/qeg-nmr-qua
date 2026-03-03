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
    n_avg=4,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.44,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=247.54,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=9125 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path.home() / "Dropbox/QEG/NMR/RawData" / Path(__file__).stem
)

cfg = qnmr.cfg_from_settings(settings)

# amp_list = np.arange(.93,1.05,.0125)
amp_list = np.arange(.975,1.03,.005)
# amp_list = np.arange(0.55, 1.1, .05)
expt = qnmr.Experiment2D(settings=settings, config=cfg)

n_wraps = 2

expt.add_pulse(element=settings.res_key, amplitude=amp_list)

for i in range(n_wraps * 4):
    expt.add_delay(2*u.us)
    expt.add_pulse(element=settings.res_key, amplitude=amp_list)

expt.update_sweep_axis(amp_list*settings.pulse_amplitude)
expt.update_sweep_label("Pulse Amplitude (Vpp)")
expt.execute_experiment()
# expt.remove_initial_delay()
# expt.simulate_experiment()

fit = False

if fit:
    
    fig = plt.figure()
    re = np.array(expt.save_data_dict["I_data"])*1e6
    power = np.array(expt.save_data_dict["sweep_axis"])

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

    plt.show()