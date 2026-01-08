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
    pulse_amplitude=0.422,  # amplitude is 0.5*Vpp
    rotation_angle=248,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=4250 * u.Hz,
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
t2 = 2 * t1 - p1

# Pine-8 sequence pattern for engineering DQ
pine8_phases = np.array([0,0,0,0,180,180,180,180])
pine8_delays = np.array([thlf, t2, t1, t2, t1, t2, t1, t2, thlf])

# evolve for up to 24 periods, 0 to 24
period_list = np.arange(0,25,1)

# define experiment object
expt = qnmr.Experiment2D(settings=settings, config=cfg)

expt.add_frame_change(angle=5.50, element=settings.res_key)

expt.add_floquet_sequence(phases=pine8_phases, delays=pine8_delays, repetitions=period_list)

expt.add_delay(1*u.ms)

expt.add_pulse(name=settings.pi_half_key, element=settings.res_key)

expt.update_sweep_axis(period_list)
expt.update_sweep_label("Pine-8 Periods")
expt.execute_experiment()

fit = True
if fit:
    fig = plt.figure()
    re = np.array(expt.save_data_dict["I_data"])*1e6
    signal = re[:,0]/re[0,0]  # normalize to first point
    periods = np.array(expt.save_data_dict["sweep_axis"])

    def damped_bessel(x, A, k, tau, b):
        return A * jn(0, k * x) * np.exp(-(x / tau)) + b
    
    # Fit the signal to the Bessel function
    popt, pcov = curve_fit(damped_bessel, periods, signal, p0=[1, 0.1, 1, 0])

    # Extract the fitted parameters
    amplitude_fit, scale_fit, tau_fit, b_fit = popt

    # Generate fitted data
    x_fit = np.linspace(min(periods), max(periods), 500)
    y_fit = damped_bessel(x_fit, *popt)

    # Plot the fitted Bessel function
    plt.scatter(periods, signal, label='Data Points')
    plt.plot(x_fit, y_fit, color='red', label='Fitted Bessel Function')
    plt.legend()

    plt.show()

    print(f"Fitted parameters: amplitude = {amplitude_fit:.3f}, scale = {scale_fit:.3f}, tau = {tau_fit:.3f}")


    
    