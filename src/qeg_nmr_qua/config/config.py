"""
OPX-1000 Configuration Module.

This module provides configuration utilities for the OPX-1000 LF-FEM
for solid state NMR experiments.
"""

from dataclasses import dataclass, field
from typing import Any
from qeg_nmr_qua.config.controller import ControllerConfig
from qeg_nmr_qua.config.element import ElementConfig
from qeg_nmr_qua.config.pulse import PulseConfig
from qeg_nmr_qua.config.waveform import AnalogWaveformConfig, DigitalWaveformConfig
from qeg_nmr_qua.config.integration import IntegrationWeights


@dataclass
class OPXConfig:
    """
    Configuration class for OPX-1000 with NMR applications in mind.

    Attributes:
        qop_ip (str): IP address of the QOP.
        cluster (str): Name of the cluster to use.
    """

    qop_ip: str = "192.168.88.253"
    cluster: str = "lex"

    controllers: ControllerConfig = field(default_factory=ControllerConfig)
    elements: ElementConfig = field(default_factory=ElementConfig)
    pulses: PulseConfig = field(default_factory=PulseConfig)
    waveforms: AnalogWaveformConfig = field(default_factory=AnalogWaveformConfig)
    digital_waveforms: DigitalWaveformConfig = field(
        default_factory=DigitalWaveformConfig
    )
    integration_weights: IntegrationWeights = field(default_factory=IntegrationWeights)

    def to_dict(self) -> dict[str, Any]:
        """Convert the OPX configuration to a dictionary."""
        return {
            "qop_ip": self.qop_ip,
            "cluster": self.cluster,
            "controllers": self.controllers.to_dict(),
            "elements": self.elements.to_dict(),
            "pulses": self.pulses.to_dict(),
            "waveforms": self.waveforms.to_dict(),
            "digital_waveforms": self.digital_waveforms.to_dict(),
            "integration_weights": self.integration_weights.to_dict(),
        }

    def to_opx_config(self) -> dict[str, Any]:
        """Convert to OPX configuration format."""
        return {
            "controllers": self.controllers.to_dict(),
            "elements": self.elements.to_dict(),
            "pulses": self.pulses.to_dict(),
            "waveforms": self.waveforms.to_dict(),
            "digital_waveforms": self.digital_waveforms.to_dict(),
            "integration_weights": self.integration_weights.to_dict(),
        }
