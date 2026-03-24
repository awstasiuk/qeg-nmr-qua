from ast import operator

import qeg_nmr_qua as qnmr

import json
from pathlib import Path
from qualang_tools.units import unit
import matplotlib.pyplot as plt
import numpy as np
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
    rotation_angle=249.5,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=10450 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path.home() / "Dropbox/QEG/NMR/RawData" / Path(__file__).stem
)

cfg = qnmr.cfg_from_settings(settings)

execute = False # whether to execute a new experiment or load from previous JSON file
if not execute: data_path = settings.save_dir / "experiment_0011/data.json"

rho0 = "Y" # evolve either X,Y,Z operator under DQ (& measure corresponding observable)
kick_axis = "Y" # apply X,Y,Z kick to the system, observe MQC intensities from function of kick angle
mqc_plot = True # whether to plot MQC intensities at the end
remove_echo_decay = True # For observing operator spreading |Cₘ(t)|² / Σₘ|Cₘ(t)|²

# sequence time constants
t0 = 5 * u.us
p1 = settings.pulse_length
thlf = (t0 - p1) / 2
t1 = t0 - p1
t2 = 2 * t0 - p1

# Pine-8 sequence pattern for engineering +/- DQ
pine8_phases = np.array([0, 0, 0, 0, 180, 180, 180, 180])
pine8_bwd_phases = np.array([90, 90, 90, 90, 270, 270, 270, 270])
pine8_delays = np.array([thlf, t2, t1, t2, t1, t2, t1, t2, thlf])

M = 2  # number of coherences
kick_angles = np.arange(0, 360, 180 / M)  # degrees, from 0 to 360 in steps of 180/M

# evolve for up to 24 periods, 0 to 24
period_list = np.arange(0, 25, 1)

# define experiment object
expt = qnmr.Experiment3D(settings=settings, config=cfg)

fc_elements = (settings.res_key, settings.helper_key)
expt.add_frame_change(angle=-2.75, elements=fc_elements)

# rotate to evolve X, Y, or Z state operator under DQ
if rho0 == "X": expt.add_pulse(phase=90, element=settings.res_key)
elif rho0 == "Y": expt.add_pulse(phase=0, element=settings.res_key)
elif rho0 == "Z": pass
else: raise ValueError("Invalid operator choice. Must be 'X', 'Y', or 'Z'.")
expt.add_delay(2.5*u.us)

# rho0, evolve under DQ
expt.add_floquet_sequence(
    phases=pine8_phases, delays=pine8_delays, repetitions=period_list, loop_layer=1
)

# rotate rho(t) by variable angle about kick_axis
if kick_axis == "X": # R_X(theta) = R_Y(-pi/2) R_Z(theta) R_Y(pi/2)
    expt.add_pulse(phase=270, element=settings.res_key)
    expt.add_delay(2.5*u.us)
    expt.add_z_rotation(angle=kick_angles, elements=(settings.res_key, settings.helper_key), loop_layer=2)
    expt.add_delay(2.5*u.us)
    expt.add_pulse(phase=90, element=settings.res_key)
elif kick_axis == "Y": # R_Y(theta) = R_X(pi/2) R_Z(theta) R_X(-pi/2)
    expt.add_pulse(phase=0, element=settings.res_key)
    expt.add_delay(2.5*u.us)
    expt.add_z_rotation(angle=kick_angles, elements=(settings.res_key, settings.helper_key), loop_layer=2)
    expt.add_delay(2.5*u.us)
    expt.add_pulse(phase=180, element=settings.res_key)
elif kick_axis == "Z": # R_Z(theta) is just a Z rotation
    expt.add_z_rotation(angle=kick_angles, elements=(settings.res_key, settings.helper_key), loop_layer=2)
else: raise ValueError("Invalid kick axis choice. Must be 'X', 'Y', or 'Z'.")

# reverse evolution via -DQ
expt.add_floquet_sequence(
    phases=pine8_bwd_phases, delays=pine8_delays, repetitions=period_list, loop_layer=1
)

# rotate back to measure X, Y, or Z observable
expt.add_delay(2.5*u.us)
if rho0 == "X": expt.add_pulse(phase=270, element=settings.res_key)
elif rho0 == "Y": expt.add_pulse(phase=180, element=settings.res_key)
elif rho0 == "Z": pass
else: raise ValueError("Invalid operator choice. Must be 'X', 'Y', or 'Z'.")

# filter transients and measure
expt.add_delay(1 * u.ms)
expt.add_pulse(element=settings.res_key)

expt.update_sweep_axis_inner(kick_angles)
expt.update_sweep_axis_outer(period_list)
expt.update_sweep_label_inner("Interior Z Rotation Angle (degrees)")
expt.update_sweep_label_outer("Floquet Periods")

if execute:
    expt.execute_experiment()
    # expt.remove_initial_delay()
    # expt.simulate_experiment()

if mqc_plot:
    
    if execute: data_dict = expt.save_data_dict
    else:
        # Load JSON file from a previous experiment if not executing current one
        with open(data_path, "r") as f:
            data_dict = json.load(f)

    re = np.array(data_dict["I_data"]) * 1e6
    im = np.array(data_dict["Q_data"]) * 1e6
    periods = np.array(data_dict["sweep_axis_outer"])
    rotation_deg = np.array(data_dict["sweep_axis_inner"])
    re = re[:, :, 0]  # Plot first point of FID for each period & rotation
    n_periods, n_phi = re.shape

    # error bars from standard deviation of im tail
    n_tail = min(20, im.shape[2])
    noise_floor = np.std(im[:, :, -n_tail:], axis=2)  # shape (period, phi)
    std = np.mean(noise_floor, axis=1)  # shape (period,)
    std_mqc = std[:, None] / np.sqrt(n_phi) # Propagate noise to MQC intensities (magnitude of FFT)

    if remove_echo_decay: # normalize to φ=0 to remove echo decay envelope and observe operator spreading
        signal = re / re[:, 0][:, np.newaxis] 
        std_mqc = std_mqc / re[:, 0][:, np.newaxis]
        
    else: # preserve echo decay envelope, observe MQC intensities more quantitatively
        signal = re / re[0,0]

    # FFT over φ to extract MQC intensities
    rotation_rad = np.deg2rad(rotation_deg)
    dphi = np.mean(np.diff(rotation_rad))
    mqc = np.fft.fft(signal, axis=1) / n_phi
    mqc = np.fft.fftshift(mqc, axes=1)
    mqc_intensity = np.abs(mqc)
    coherence_orders = np.fft.fftshift(np.fft.fftfreq(n_phi, d=dphi/(2*np.pi))) # Frequency axis (coherence order)
    # deal with the fact that we test kicks [0, 360) 
    idx_min = np.argmin(coherence_orders)  # Duplicate minimum coherence at max + 1
    coherence_orders = np.append(coherence_orders, np.max(coherence_orders) + 1)
    mqc_intensity = np.column_stack([mqc_intensity, mqc_intensity[:, idx_min]])

    # second moment
    allowed = np.isin(coherence_orders, [0, -2, 2])
    I_sel = mqc_intensity[:, allowed]
    m_sel = coherence_orders[allowed]
    m2_restricted = np.sum((m_sel**2) * I_sel, axis=1) / np.sum(I_sel, axis=1)

    # 3D Plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # render MQC intensity of each order back to front
    sort_idx = np.argsort(coherence_orders)[::-1]
    for j in sort_idx:
        # gray out lines where MQC intensity < 3σ stddev to de-emphasize noise floor
        if np.mean(mqc_intensity[:-10, j]) < 0.05 :
            color = 'darkgray'
        else: color = None
        
        # Fit the signal to the Bessel^2 function
        if j==2:
            def damped_bessel2(x, A, k, tau, b, x0):
                return (A * (jn(0, k * x - x0))**2 + b) * np.exp(- (x / tau))
            popt, pcov = curve_fit(damped_bessel2, periods, mqc_intensity[:,j], bounds=([0, 0, 0.0, 0, -2], [2, 2, 9999, 1, 2]) )
            amplitude_fit, scale_fit, tau_fit, b_fit, x0_fit = popt
            x_fit = np.linspace(min(periods), max(periods), 500)
            y_fit = damped_bessel2(x_fit, *popt)

        ax.plot(periods, np.full_like(periods, coherence_orders[j]), 
                (mqc_intensity[:, j]), color=color, zorder=999)
        if j==2: ax.plot(x_fit, np.full_like(x_fit, coherence_orders[j]), 
                (y_fit), color=color, zorder=999)
        ax.errorbar(periods, np.full_like(periods, coherence_orders[j]), mqc_intensity[:, j], 
                zerr=2*std_mqc[:, 0], fmt='none', ecolor='darkgray', alpha=0.5, zorder=1)

    ax.set_xlabel("Floquet Periods"); ax.set_xlim(0, periods.max())
    ax.set_ylabel("Coherence Order"); ax.set_yticks(np.arange(coherence_orders.min(), coherence_orders.max()+1, step=2))
    ax.set_zlabel("MQC Intensity"); ax.set_zlim(0, mqc_intensity.max())

    plt.title("MQC Intensities" + (" (Normalized Echo Decay)" if remove_echo_decay else ""))
    plt.tight_layout()
    plt.show()

    print(f"Fitted parameters for m=2 Bessel decay: amplitude = {amplitude_fit:.3f}, scale = {scale_fit:.3f}, tau = {tau_fit:.3f}, baseline = {b_fit:.3f}, x0 = {x0_fit:.3f}")
    plt.figure()
    plt.plot(periods, m2_restricted, 'o-')
    plt.xlabel("Floquet Periods")
    plt.ylabel("⟨$m^2$⟩")
    plt.title("MQC Second Moment")
    plt.show()