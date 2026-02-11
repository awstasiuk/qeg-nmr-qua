import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
import numpy as np
from statsmodels.tsa.stattools import acf

u = unit(coerce_to_integer=True)


def phase_calibration(settings):
    """
    Perform phase calibration using a 1D FID experiment to determine the phase drift
    of the nuclear spin frequency reference.

    Args:
        settings (ExperimentSettings): Experiment settings object.

    Returns:
        float: Estimated phase drift in degrees.
    """
    config = qnmr.cfg_from_settings(settings)
    expt = qnmr.Experiment1D(settings, config)
    expt.add_pulse(element=settings.res_key)
    expt.execute_experiment(
        live=True, wait_on_close=False, title_prefix="[Phase Calibration] "
    )

    I = expt.save_data_dict["I_data"]
    Q = expt.save_data_dict["Q_data"]

    delphi = np.arctan2(Q[0], I[0]) * (180 / np.pi)
    settings.rotation_angle += round(delphi, 2)
    print("Incrementing phase reference by {:.2f} degrees".format(delphi))
    print("Updated rotation angle to {:.2f} degrees".format(settings.rotation_angle))
    # return delphi


def check_offset(settings):
    """
    Perform offset frequency calibration using a 1D FID experiment to determine
    the optimal offset frequency.

    Args:
        settings (ExperimentSettings): Experiment settings object.

    Returns:
        int: Either 0 if the offset frequency is acceptable, 1 if it needs to be increase,
            or -1 if it needs to be decreased.
    """
    config = qnmr.cfg_from_settings(settings)
    expt = qnmr.Experiment1D(settings, config)
    expt.add_pulse(element=settings.res_key)
    expt.execute_experiment(
        live=True, wait_on_close=False, title_prefix="[Offset Check] "
    )

    Q = expt.save_data_dict["Q_data"]

    # Calculate the autocorrelation of the signal
    autocorr = acf(Q, nlags=len(Q) - 1, fft=True)
    confidence_95 = 1.96 / np.sqrt(len(Q))

    # Compute the number of entries in autocorr greater than confidence_95
    num_entries_above_threshold = np.sum(abs(autocorr) > confidence_95)

    if num_entries_above_threshold <= 3:
        return 0  # offset frequency is acceptable
    else:
        if np.mean(Q[:5]) > 0:
            return 1  # increase offset frequency
        else:
            return -1  # decrease offset frequency


def bisection_offset_calibration(
    settings, delta=500 * u.Hz, max_iters=10, tol=50 * u.Hz
):
    """
    Perform offset frequency calibration using a bisection method to find the optimal offset frequency.

    Args:
        settings (ExperimentSettings): Experiment settings object.
        tol (int): Tolerance for the offset frequency in Hz.
        max_iters (int): Maximum number of iterations for the bisection method.

    Returns:
        bool: If we successfully calibrated the offset frequency.
    """
    a = settings.offset_freq
    b = settings.offset_freq + delta

    # check that b is actually on the other side of the root
    for _ in range(max_iters):
        settings.offset_freq = b
        phase_calibration(settings)
        result = check_offset(settings)
        if result == 0:
            print("Offset frequency calibrated to {:.2f} Hz".format(b))
            return True  # we are calibrated sufficiently
        elif result == 1:
            b += delta
        else:
            break  # b is on the other side

    for _ in range(max_iters):
        mid_offset = (a + b) / 2
        settings.offset_freq = mid_offset
        phase_calibration(settings)
        result = check_offset(settings)

        if result == 0:
            print("Offset frequency calibrated to {:.2f} Hz".format(mid_offset))
            return True
        elif result == 1:
            a = mid_offset
        else:
            b = mid_offset

        if abs(b - a) < tol:
            print(
                "Offset frequency calibration too narrow, check autocorrelation manually."
            )
            break

    print(
        "Offset Calibration failed - final offset frequency is {:.2f} Hz".format(
            mid_offset
        )
    )
    return False


def pulse_amp_calibration(settings, n_wraps=2):
    """
    Placeholder for pulse amplitude calibration function.
    """
    config = qnmr.cfg_from_settings(settings)
    amp_scaling = np.arange(0.94, 1.06, 0.01)
    expt = qnmr.Experiment2D(settings=settings, config=config)

    expt.add_pulse(element=settings.res_key, amplitude=amp_scaling)

    for i in range(n_wraps * 4):
        expt.add_pulse(element=settings.res_key, amplitude=amp_scaling)
        expt.add_delay(2 * u.us)

    expt.update_sweep_axis(amp_scaling * settings.pulse_amplitude)
    expt.execute_experiment(
        live=True,
        wait_on_close=False,
        title_prefix=f"[Pulse Amplitude Cal - {n_wraps} wraps] ",
    )

    re = np.array(expt.save_data_dict["I_data"]) * 1e6
    sig = re[:, 0]
    power = np.array(expt.save_data_dict["sweep_axis"])
    coefficients = np.polyfit(power, sig, 2)

    max_amp = -coefficients[1] / (2 * coefficients[0])
    settings.pulse_amplitude = max_amp
    print(
        f"Updated pulse amplitude to {max_amp:.3f} Vpp after maxing over {n_wraps} Bloch sphere wraps."
    )
