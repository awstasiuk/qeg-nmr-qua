"""
This example shows how to set up and visualize a simple free induction decay (FID)
experiment using the qeg_nmr_qua package. The experiment applies a single
π/2 pulse to the nuclear spin system and measures the resulting FID signal.

This reproduces the "zero-go" function often used in Brucker systems.
"""

import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import acf

u = unit(coerce_to_integer=True)

# create base settings object for experiments
settings = qnmr.ExperimentSettings(
    n_avg=4,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.48,  # amplitude is 0.5*Vpp
    pulse_shape="square",
    pulse_rise_fall=0.0,  # 0% rise/fall time
    rotation_angle=247.54,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=9250 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path.home() / "Dropbox/QEG/NMR/RawData" / Path(__file__).stem,
)

cfg = qnmr.cfg_from_settings(settings)

# write an experiment which measures a basic FID signal
expt = qnmr.Experiment1D(
    config=cfg,
    settings=settings,
    connect=False,
)

expt.add_pulse(element=settings.res_key, phase=[0, 90, 180, 270], phase_cycle=True)

viz = qnmr.SequenceVisualizer(expt, settings, cfg)

viz.plot()
