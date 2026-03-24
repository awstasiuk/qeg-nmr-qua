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

loschmidt_expt = False # whether to execute Loschmidt echo or just forward evolution
cfg = qnmr.cfg_from_settings(settings)

# sequence time constants
t0 = 5*u.us
p1 = settings.pulse_length
thlf = (t0 - p1) / 2
t1 = t0 - p1
t2 = 2 * t0 - p1

# define experiment object
expt = qnmr.Experiment2D(settings=settings, config=cfg)

fc_elements = (settings.res_key, settings.helper_key)
expt.add_frame_change(angle=-4.9, elements=fc_elements)


# Pine-8 sequence pattern for engineering H=0
pine8_phases = np.array([0,0,0,0,180,180,180,180])
pine8_bw_phases = np.array([90,90,90,90,270,270,270,270])
pine8_delays = np.array([thlf, t2, t1, t2, t1, t2, t1, t2, thlf])
# evolve for up to 24 periods, 0 to 24
period_list = np.arange(0,25,1)
expt.add_floquet_sequence(phases=pine8_phases, delays=pine8_delays, repetitions=period_list)
expt.update_sweep_label("Pine-8 Periods")
if loschmidt_expt:
    expt.add_floquet_sequence(phases=pine8_bw_phases, delays=pine8_delays, repetitions=period_list)
    expt.update_sweep_label("Pine-8 (fwd & bwd) Periods")


expt.add_delay(1*u.ms)
expt.add_pulse(element=settings.res_key)

expt.update_sweep_axis(period_list)

expt.execute_experiment()
# expt.remove_initial_delay()
# expt.simulate_experiment()

fit = True
if fit:
    data_dict = expt.save_data_dict
    re = np.array(expt.save_data_dict["I_data"])*1e6
    periods = np.array(expt.save_data_dict["sweep_axis"])
    signal = re[:,0]/re[0,0]  # normalize to first point

    if loschmidt_expt: 
        # Log transform; only positive values
        mask = signal > 0; x, y = periods[mask], signal[mask]

        def stretched_exp(x, A, tau, beta):
            return A * np.exp(-(x/tau)**beta)

        popt, _ = curve_fit(stretched_exp, x, y, p0=[1.0, 1.0, 1.0])
        amplitude_fit, tau_fit, beta_fit = popt
        
        # Generate fitted curve (back in linear space)
        x_fit = np.linspace(min(periods), max(periods), 500)
        y_fit = stretched_exp(x_fit, amplitude_fit, tau_fit, beta_fit)
        
        # Create side-by-side plots
        fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(10, 4))

        # Linear plot
        ax_lin.scatter(periods, signal, label='Data')
        ax_lin.plot(x_fit, y_fit, 'r',
                    label=f'A={amplitude_fit:.2f}, τ={tau_fit:.2f}, β={beta_fit:.2f}')
        ax_lin.set_title("Linear scale")
        ax_lin.set_xlabel("Periods")
        ax_lin.set_ylabel("Signal")
        ax_lin.legend()

        # Log-linear plot
        ax_log.scatter(x, np.log(y), label='log(Data)')
        ax_log.plot(x_fit, np.log(y_fit), 'r', label='stretched exponential fit')
        ax_log.set_title("Log-linear scale")
        ax_log.set_xlabel("Periods")
        ax_log.set_ylabel("log(Signal)")
        ax_log.legend()

        print(f"Fitted parameters: A = {amplitude_fit:.3f}, tau = {tau_fit:.3f}, beta = {beta_fit:.3f}")
    
    # fwd evolution only, fit to damped Bessel
    else: 
        fig = plt.figure()

        def damped_bessel(x, A, k, tau, b):
            return A * jn(0, k * x) * np.exp(-(x / tau)) + b
        
        # Fit the signal to the Bessel function; expected values listed in p0
        popt, pcov = curve_fit(damped_bessel, periods, signal, p0=[1, 1.4, 12, 0], 
                            bounds = ([0.5, 0.5, 1.0, -0.5], [2.0, 3.0, 30.0, 0.5]) )

        # Extract the fitted parameters
        amplitude_fit, scale_fit, tau_fit, b_fit = popt

        # Generate fitted data
        x_fit = np.linspace(min(periods), max(periods), 500)
        y_fit = damped_bessel(x_fit, *popt)

        # Plot the fitted Bessel function
        plt.scatter(periods, signal, label='Data Points')
        plt.plot(x_fit, y_fit, color='red', label='Fitted Bessel Function')
        plt.legend()
        print(f"Fitted parameters: amplitude = {amplitude_fit:.3f}, scale = {scale_fit:.3f}, tau = {tau_fit:.3f}")

    plt.tight_layout()
    plt.show()