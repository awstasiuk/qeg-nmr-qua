"""
QEG NMR QUA - NMR Control using the OPX-1000 LF-FEM.

This package provides tools for controlling the OPX-1000 low-frequency
front-end module for solid state nuclear magnetic resonance experiments,
particularly for fluorine spins.
"""

from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.data_saver import DataSaver
from qeg_nmr_qua.live_plotter import LivePlotter

__version__ = "0.1.0"

__all__ = [
    "OPXConfig",
    "DataSaver",
    "LivePlotter",
    "__version__",
]
