import tempfile
from pathlib import Path


import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.special import jn

u = unit(coerce_to_integer=True)


settings = qnmr.ExperimentSettings(
    n_avg=4,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.485,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=251.0,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=8425 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path.home() / "Dropbox/QEG/NMR/RawData" / Path(__file__).stem,
)

cfg = qnmr.cfg_from_settings(settings)


expt = qnmr.Experiment1D(
    settings=settings,
    config=cfg,
    connect=False,
)

expt.add_pulse(element=settings.res_key, phase=[0, 90, 180, 270], phase_cycle=True)

expt.compile_to_qua(offline=True)
