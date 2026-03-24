"""
This example shows how to set up and run a simple relaxation time experiment
using the qeg_nmr_qua package. The experiment applies a series of pulses to
the nuclear spin system to engineer the effective Hamiltonian H=0, and 
measures the resulting signal decay.

This experiment uses the "peng-24" or "angle-12" sequence described in the
paper "Frame change technique for phase transient cancellation."  Stasiuk, 
Andrew, et al., Journal of Magnetic Resonance 362 (2024): 107688.
"""

import qeg_nmr_qua as qnmr

import json
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
    pulse_length=1.12 * u.us,
    pulse_amplitude=0.483,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=249.05,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=10600 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path.home() / "Dropbox/QEG/NMR/RawData" / Path(__file__).stem
)

cfg = qnmr.cfg_from_settings(settings)
execute_peng24 = False # whether to execute the peng-24 or angle-12 sequence
execute = False # whether to execute a new experiment or load from previous JSON file
if not execute: data_path = Path.home() / "Dropbox/QEG/NMR/RawData" / "test_peng24_expt/experiment_0012/data.json"

# sequence time constants
t0 = 5*u.us
p1 = settings.pulse_length
thlf = (t0 - p1) // 2
t1 = t0 - p1
t2 = 2 * t0 - p1 

# define experiment object
expt = qnmr.Experiment2D(settings=settings, config=cfg)

fc_elements = (settings.res_key, settings.helper_key)
expt.add_frame_change(angle=-2.6, elements=fc_elements)

expt.add_pulse(element=settings.res_key)
expt.add_delay(thlf)

# Peng-24 sequence pattern for engineering H=0
if execute_peng24:
    yxx24_phases = np.array([270,0,180,  90,180,180,  270,0,180,  90,0,0,
                            90,180,0,  270,0,0,  90,180,0,  270,180,180])
    yxx24_delays = np.array([thlf,t1,t1,t1,  t1,t1,t1,  t1,t1,t1,  t1,t1,t1,
                            t1,t1,t1,  t1,t1,t1,  t1,t1,t1,  t1,t1,thlf])
    # evolve for up to 24 periods, 0 to 24
    period_list = np.arange(0,200,8)
    expt.add_floquet_sequence(phases=yxx24_phases, delays=yxx24_delays, repetitions=period_list)
    expt.add_delay(thlf)
    expt.add_pulse(phase=180, element=settings.res_key)
    expt.update_sweep_label("Peng-24 Periods")


# Angle-12 sequence pattern
else:
    angle12_phases = np.array([270,0,180,  90,180,180,  270,0,180,  90,0,0])
    angle12_reverse_phases = np.array([90,180,0,  270,0,0,  90,180,0,  270,180,180])
    angle12_delays = np.array([thlf,t1,t1,t1,  t1,t1,t1,  t1,t1,t1,  t1,t1,thlf])
    # evolve for up to 15 periods, 0 to 15
    period_list = np.arange(0,16,1)
    expt.add_floquet_sequence(phases=angle12_phases, delays=angle12_delays, repetitions=period_list)
    expt.update_sweep_label("Angle-12 Periods")


expt.add_delay(1*u.ms)
expt.add_pulse(element=settings.res_key)

expt.update_sweep_axis(period_list)

if execute:
    expt.execute_experiment()

fit = True
if fit:
    if execute: data_dict = expt.save_data_dict
    else:
        # Load JSON file from a previous experiment if not executing current one
        with open(data_path, "r") as f:
            data_dict = json.load(f)

    re = np.array(data_dict["I_data"]) * 1e6
    periods = np.array(data_dict["sweep_axis"])
    signal = re[:,0]/re[0,0]  # normalize to first point

    # Log transform; only positive values
    mask = signal > 0; x, y = periods[mask], signal[mask]
    log_y = np.log(y)

    def stretched_exp(x, A, tau, beta):
        return A * np.exp(-(x/tau)**beta)

    popt, _ = curve_fit(stretched_exp, x, y, p0=[1.0, 1.0, 1.0])
    amplitude_fit, tau_fit, beta_fit = popt
    
   # Generate fitted curve (back in linear space)
    x_fit = np.linspace(min(periods), max(periods), 500)
    y_fit = stretched_exp(x_fit, amplitude_fit, tau_fit, beta_fit)
    log_y_fit = np.log(y_fit)
    
    # Create side-by-side plots
    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(10, 4))

    # Linear plot
    ax_lin.scatter(periods, signal, label='Data')
    ax_lin.plot(x_fit, y_fit, 'r', label=f'A={amplitude_fit:.2f}, τ={tau_fit:.2f}, β={beta_fit:.2f}')
    ax_lin.set_title("Linear scale")
    ax_lin.set_xlabel("Periods")
    ax_lin.set_ylabel("Signal")
    ax_lin.legend()

    # Log-linear plot
    ax_log.scatter(x, log_y, label='log(Data)')
    ax_log.plot(x_fit, log_y_fit, 'r', label='stretched exponential fit')
    ax_log.set_title("Log-linear scale")
    ax_log.set_xlabel("Periods")
    ax_log.set_ylabel("log(Signal)")
    ax_log.legend()

    plt.tight_layout()
    plt.show()

    print(f"Fitted parameters: A = {amplitude_fit:.3f}, tau = {tau_fit:.3f}, beta = {beta_fit:.3f}")