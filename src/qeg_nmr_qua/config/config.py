"""
OPX-1000 Configuration Module.

This module provides configuration utilities for the OPX-1000 LF-FEM
for solid state NMR experiments.
"""

from dataclasses import dataclass, field
from typing import Any
from collections.abc import Iterable

from qeg_nmr_qua.config.controller import ControllerConfig
from qeg_nmr_qua.config.element import ElementConfig, Element
from qeg_nmr_qua.config.pulse import PulseConfig, ControlPulse, MeasPulse
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
            "controllers": self.controllers.to_opx_config(),
            "elements": self.elements.to_opx_config(),
            "pulses": self.pulses.to_opx_config(),
            "waveforms": self.waveforms.to_opx_config(),
            "digital_waveforms": self.digital_waveforms.to_opx_config(),
            "integration_weights": self.integration_weights.to_opx_config(),
        }

    def add_controller(self, controller_config: ControllerConfig):
        """Add a controller configuration."""
        self.controllers = controller_config

    def add_element(self, name: str, element: Element):
        self.elements.add_element(name, element)

    def add_pulse(self, name: str, pulse: ControlPulse | MeasPulse):
        """Add a pulse configuration."""
        self.pulses.add_pulse(name, pulse)

    def add_waveform(self, name: str, waveform: float | list[float]):
        """Add an analog waveform configuration."""
        wf_type = "arbitrary" if isinstance(waveform, Iterable) else "constant"
        self.waveforms.add_waveform(name, wf_type=wf_type, sample=waveform)

    def add_digital_waveform(self, name: str, state: int = 0, length: int = 0):
        """Add a digital waveform (marker) configuration."""
        self.digital_waveforms.add_waveform(name, state=state, length=length)

    def add_integration_weight(
        self, name: str, length: int, real_weight: float = 1, imag_weight: float = 0
    ):
        """Add an integration weight configuration."""
        self.integration_weights.add_weight(
            name, length, real_weight=real_weight, imag_weight=imag_weight
        )
