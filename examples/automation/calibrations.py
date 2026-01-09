import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import acf

u = unit(coerce_to_integer=True)


def phase_calibration(settings, config):
    """
    Perform phase calibration using a 1D FID experiment to determine the phase drift
    of the nuclear spin frequency reference.

    Args:
        settings (ExperimentSettings): Experiment settings object.
        config (OPXConfig): OPX configuration object.

    Returns:
        float: Estimated phase drift in degrees.
    """
    expt = qnmr.Experiment1D(config, settings)
    expt.add_pulse(name=settings.pi_half_key, element=settings.res_key)
    expt.execute_experiment()

    I = expt.save_data_dict["I"]
    Q = expt.save_data_dict["Q"]

    delphi = np.arctan2(Q[0], I[0]) * (180 / np.pi)
    settings.rotation_angle += delphi
    print("Incrementing phase reference by {:.2f} degrees".format(delphi))
    # return delphi


def check_offset(settings, config):
    """
    Perform offset frequency calibration using a 1D FID experiment to determine
    the optimal offset frequency.

    Args:
        settings (ExperimentSettings): Experiment settings object.
        config (OPXConfig): OPX configuration object.

    Returns:
        int: Either 0 if the offset frequency is acceptable, 1 if it needs to be increase,
            or -1 if it needs to be decreased.
    """
    expt = qnmr.Experiment1D(config, settings)
    expt.add_pulse(name=settings.pi_half_key, element=settings.res_key)
    expt.execute_experiment()

    Q = expt.save_data_dict["Q"]

    # Calculate the autocorrelation of the signal
    autocorr = acf(Q, nlags=len(Q) - 1, fft=True)
    confidence_95 = 1.96 / np.sqrt(len(Q))

    # Compute the number of entries in autocorr greater than confidence_95
    num_entries_above_threshold = np.sum(abs(autocorr) > confidence_95)

    if num_entries_above_threshold <= 2:
        return 0  # offset frequency is acceptable
    else:
        if np.mean(Q[:5]) > 0:
            return 1  # increase offset frequency
        else:
            return -1  # decrease offset frequency


def bisection_offset_calibration(
    settings, config, delta=500 * u.Hz, max_iters=10, tol=50 * u.Hz
):
    """
    Perform offset frequency calibration using a bisection method to find the optimal offset frequency.

    Args:
        settings (ExperimentSettings): Experiment settings object.
        config (OPXConfig): OPX configuration object.
        tol (int): Tolerance for the offset frequency in Hz.
        max_iters (int): Maximum number of iterations for the bisection method.

    Returns:
        float: Estimated optimal offset frequency in Hz.
    """
    a = settings.offset_freq
    b = settings.offset_freq + delta

    # check that b is actually on the other side of the root
    for _ in range(max_iters):
        settings.offset_freq = b
        phase_calibration(settings, config)
        result = check_offset(settings, config)
        if result == 0:
            return b  # we are calibrated sufficiently
        elif result == 1:
            b += delta
        else:
            break  # b is on the other side

    for _ in range(max_iters):
        mid_offset = (lower_bound + upper_bound) / 2
        settings.offset_freq = mid_offset
        phase_calibration(settings, config)
        result = check_offset(settings, config)

        if result == 0:
            print("Offset frequency calibrated to {:.2f} Hz".format(mid_offset))
            return mid_offset
        elif result == 1:
            lower_bound = mid_offset
        else:
            upper_bound = mid_offset

        if abs(upper_bound - lower_bound) < tol:
            print(
                "Offset frequency calibration too narrow, check autocorrelation manually."
            )
            break

    print(
        "Offset Calibration failed - final offset frequency is {:.2f} Hz".format(
            mid_offset
        )
    )
