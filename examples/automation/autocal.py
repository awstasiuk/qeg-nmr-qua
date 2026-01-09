import qeg_nmr_qua as qnmr
from calibrations import *

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import acf

u = unit(coerce_to_integer=True)

# create a starting point for the automated calibration script
settings = qnmr.ExperimentSettings(
    n_avg=2,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.4095,  # amplitude is 0.5*Vpp
    rotation_angle=250.94,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=4500 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "data",
)

saver = qnmr.DataSaver(settings.save_dir)
saver.save_settings(settings, "autocal_settings", overwrite=True)

cfg = qnmr.cfg_from_settings(settings)
phase_calibration(settings, cfg)
saver.save_settings(settings, "autocal_settings", overwrite=True)

cfg = qnmr.cfg_from_settings(settings)
if check_offset(settings, cfg) != 0:
    success = bisection_offset_calibration(settings, cfg)

if success:
    # calibrate pulse power
    settings.n_avg = 4
    saver.save_settings(settings, "autocal_settings", overwrite=True)

    cfg = qnmr.cfg_from_settings(settings)
    pulse_amp_calibration(settings, cfg, n_wraps=2)
    saver.save_settings(settings, "autocal_settings", overwrite=True)

    cfg = qnmr.cfg_from_settings(settings)
    pulse_amp_calibration(settings, cfg, n_wraps=3)
    saver.save_settings(settings, "autocal_settings", overwrite=True)

    cfg = qnmr.cfg_from_settings(settings)
    pulse_amp_calibration(settings, cfg, n_wraps=2)
    saver.save_settings(settings, "autocal_settings", overwrite=True)
