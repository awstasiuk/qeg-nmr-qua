"""
QEG NMR QUA - NMR Control using the OPX-1000 LF-FEM.

This package provides tools for controlling the OPX-1000 low-frequency
front-end module for solid state nuclear magnetic resonance experiments,
particularly for fluorine spins.
"""

from importlib import import_module

from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.config.controller import (
    AnalogOutput,
    DigitalIO,
    AnalogInput,
    FEModuleConfig,
    ControllerConfig,
)
from qeg_nmr_qua.config.element import ElementConfig, Element
from qeg_nmr_qua.config.integration import IntegrationWeights
from qeg_nmr_qua.config.pulse import PulseConfig
from qeg_nmr_qua.config.waveform import AnalogWaveformConfig, DigitalWaveformConfig

__version__ = "0.1.0"

__all__ = [
    "OPXConfig",
    "AnalogOutput",
    "DigitalIO",
    "AnalogInput",
    "FEModuleConfig",
    "ControllerConfig",
    "Element",
    "ElementConfig",
    "IntegrationWeights",
    "PulseConfig",
    "AnalogWaveformConfig",
    "DigitalWaveformConfig",
    "DataSaver",
    "LivePlotter",
    "__version__",
]


def __getattr__(name: str):
    """Lazy-load heavy subcomponents only when accessed.

    This keeps `import qeg_nmr_qua` fast while still exposing
    `DataSaver` and `LivePlotter` as top-level attributes.
    """
    if name == "DataSaver":
        return import_module("qeg_nmr_qua.data_saver").DataSaver
    if name == "LivePlotter":
        return import_module("qeg_nmr_qua.live_plotter").LivePlotter
    if name == "OPXConfig":
        return OPXConfig
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__():
    return sorted(list(globals().keys()) + __all__)
