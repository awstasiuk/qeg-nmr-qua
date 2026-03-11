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
    pulse_length=1.12 * u.us,
    pulse_amplitude=0.475,  # amplitude is 0.5*Vpp
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
zero_cross = True # whether to find zero crossing or fit to parabola
fit = True

# amp_list = np.arange(.93,1.05,.0125)
amp_list = np.arange(.975,1.025,.005)
# amp_list = np.arange(0.55, 1.1, .05)
expt = qnmr.Experiment2D(settings=settings, config=cfg)

fc_elements = (settings.res_key, settings.helper_key)
expt.add_frame_change(angle=-4.0, elements=fc_elements)

n_wraps = 3

if zero_cross: 
    expt.add_pulse(element=settings.res_key, amplitude=amp_list)

for i in range(n_wraps*4+1):
    expt.add_delay(2*u.us)
    expt.add_pulse(element=settings.res_key, amplitude=amp_list)

expt.update_sweep_axis(amp_list*settings.pulse_amplitude)
expt.update_sweep_label("Pulse Amplitude (Vpp)")
expt.execute_experiment()
# expt.remove_initial_delay()
# expt.simulate_experiment()

if fit:
    re = np.array(expt.save_data_dict["I_data"])*1e6
    power = np.array(expt.save_data_dict["sweep_axis"])

    # find zero crossing
    if zero_cross:
        fig, ax = plt.subplots()
        sig = re[:,0]
        ax.scatter(power, sig, label="Data Points")

        # Fit to a linear curve
        coeffs = np.polyfit(power, sig, 1)
        fit_line = np.polyval(coeffs, power)
        ax.plot(power, fit_line, "--", label="Linear Fit")

        # Calculate and indicate the zero crossing
        zero_crossing = -coeffs[1] / coeffs[0]
        ax.axvline(zero_crossing, color="red", linestyle="--", label=f"Zero Crossing: {zero_crossing:.3f} Vpp")
        ax.legend()

    # fit to parabola
    else:
        fig = plt.figure()

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
        
        print(f"Maximum at x = {vertex_x}, y = {vertex_y}")

    plt.xlabel('Pulse Amplitude (Vpp)')
    plt.ylabel('FID Signal Amplitude (µV)')
    plt.title('Pulse Calibration: FID Signal vs Pulse Amplitude, {} wraps'.format(n_wraps))
    plt.show()