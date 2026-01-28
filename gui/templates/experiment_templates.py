"""Templates for experiment scripts."""

EXPERIMENT_1D_TEMPLATE = '''"""
{description}
"""

import qeg_nmr_qua as qnmr
from qualang_tools.units import unit
from pathlib import Path

u = unit(coerce_to_integer=True)

# Load active settings from GUI
settings = qnmr.ExperimentSettings.from_json("active-settings.json")

# Generate configuration from settings
cfg = qnmr.cfg_from_settings(settings)

# Create 1D experiment
expt = qnmr.Experiment1D(
    config=cfg,
    settings=settings,
)

# Build pulse sequence
expt.add_pulse(name=settings.pi_half_key, element=settings.res_key)

# Note: Execute via GUI Run button, not here
# expt.execute_experiment()
'''

EXPERIMENT_2D_TEMPLATE = '''"""
{description}
"""

import qeg_nmr_qua as qnmr
from qualang_tools.units import unit
from pathlib import Path
import numpy as np

u = unit(coerce_to_integer=True)

# Load active settings from GUI
settings = qnmr.ExperimentSettings.from_json("active-settings.json")

# Generate configuration from settings
cfg = qnmr.cfg_from_settings(settings)

# Define sweep parameter
sweep_values = np.linspace(0.5, 1.5, 50)  # Example: amplitude sweep

# Create 2D experiment
expt = qnmr.Experiment2D(
    config=cfg,
    settings=settings,
)

# Build pulse sequence with sweep
expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, amplitude=sweep_values)

# Update sweep axis labels
expt.update_sweep_axis(sweep_values * settings.pulse_amplitude)
expt.update_sweep_label("Pulse Amplitude (Vpp)")

# Note: Execute via GUI Run button, not here
# expt.execute_experiment()
'''

CUSTOM_TEMPLATE = '''"""
{description}
"""

import qeg_nmr_qua as qnmr
from qualang_tools.units import unit
from pathlib import Path
import numpy as np

u = unit(coerce_to_integer=True)

# Load active settings from GUI
settings = qnmr.ExperimentSettings.from_json("active-settings.json")

# Generate configuration from settings
cfg = qnmr.cfg_from_settings(settings)

# TODO: Create your experiment here
# Example for 1D:
# expt = qnmr.Experiment1D(config=cfg, settings=settings)
# expt.add_pulse(name=settings.pi_half_key, element=settings.res_key)

# Note: Execute via GUI Run button, not here
# expt.execute_experiment()
'''


def get_template(exp_type: str) -> str:
    """Get the template for a given experiment type."""
    templates = {
        "1D": EXPERIMENT_1D_TEMPLATE,
        "2D": EXPERIMENT_2D_TEMPLATE,
        "Custom": CUSTOM_TEMPLATE,
    }
    return templates.get(exp_type, CUSTOM_TEMPLATE)

