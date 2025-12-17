import qeg_nmr_qua as qnmr

from qualang_tools.units import unit
from pathlib import Path
import numpy as np

u = unit(coerce_to_integer=True)

# create base settings object for experiments
settings = qnmr.ExperimentSettings(
    n_avg=4,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.41,  # amplitude is 0.5*Vpp
    rotation_angle=255.0,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=2550 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "test_results",
)

cfg = qnmr.cfg_from_settings(settings)

amp_list = np.arange(.95,1.06,.01)
expt = qnmr.Experiment2D(config=cfg, settings=settings)

n_wraps = 2

for i in range(n_wraps * 4):
    expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, amplitude=amp_list)
    expt.add_delay(2*u.us)

expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, amplitude=amp_list)

#expt.remove_initial_delay()
#expt.simulate_experiment()
expt.execute_experiment()
    