import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import jn

u = unit(coerce_to_integer=True)

# create base settings object for experiments
settings = qnmr.ExperimentSettings(
    n_avg=4,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.48,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=245.50,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=7350 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "test_results",
)


cfg = qnmr.cfg_from_settings(settings)

# sequence time constants
t0 = 5*u.us
p1 = settings.pulse_length
thlf = (t0 - p1) / 2
t1 = t0 - p1
t2 = 2 * t0 - p1 

# Angle-12 sequence pattern
angle12_phases = np.array([270,0,180,  90,180,180,  270,0,180,  90,0,0])
angle12_reverse_phases = np.array([90,180,0,  270,0,0,  90,180,0,  270,180,180])
angle12_delays = np.array([thlf,t1,t1,t1,  t1,t1,t1,  t1,t1,t1,  t1,t1,thlf])

# Peng-24 sequence pattern for engineering H=0
yxx24_phases = np.array([270,0,180,  90,180,180,  270,0,180,  90,0,0,
                          90,180,0,  270,0,0,  90,180,0,  270,180,180])
yxx24_delays = np.array([thlf,t1,t1,t1,  t1,t1,t1,  t1,t1,t1,  t1,t1,t1,
                          t1,t1,t1,  t1,t1,t1,  t1,t1,t1,  t1,t1,thlf])


# evolve for up to 48 periods, 0 to 48
period_list = np.arange(0,50,2)

# define experiment object
expt = qnmr.Experiment2D(settings=settings, config=cfg)

expt.add_frame_change(angle=5.58, element=settings.res_key)

# expt.add_floquet_sequence(phases=angle12_phases, delays=angle12_delays, repetitions=period_list)
expt.add_floquet_sequence(phases=yxx24_phases, delays=yxx24_delays, repetitions=period_list)

expt.add_delay(1*u.ms)

expt.add_pulse(element=settings.res_key)

expt.update_sweep_axis(period_list)
expt.update_sweep_label("Peng-24 Periods")
expt.execute_experiment()


# import json
# file_path = r"C:\Users\NMR Lab\Documents\dev\qeg-nmr-qua\tests\test_results\experiment_0045\data.json"
# with open(file_path, "r") as f:
#     data = json.load(f)
# re =  np.array(data["I_data"]) * 1e6
# periods = np.array(data["sweep_axis"])

fit = True
if fit:
    fig = plt.figure()
    re = np.array(expt.save_data_dict["I_data"])*1e6
    periods = np.array(expt.save_data_dict["sweep_axis"])
    signal = re[:,0]/re[0,0]  # normalize to first point

    def decay(x, A, tau, b):
        return A * np.exp(-(x / tau)) + b
    
    # Fit the signal to the exponential decay function; expected values listed in p0
    popt, pcov = curve_fit(decay, periods, signal, p0=[1, 12, 0], 
                           bounds = ([0.5, 1.0, -0.5], [2.0, 30.0, 0.5]) )

    # Extract the fitted parameters
    amplitude_fit, tau_fit, b_fit = popt

    # Generate fitted data
    x_fit = np.linspace(min(periods), max(periods), 500)
    y_fit = decay(x_fit, *popt)

    # Plot the fitted decay function
    plt.scatter(periods, signal, label='Data Points')
    plt.plot(x_fit, y_fit, color='red', label='Fitted Decay Function')
    plt.legend()

    plt.show()

    print(f"Fitted parameters: amplitude = {amplitude_fit:.3f}, tau = {tau_fit:.3f}")


    
    