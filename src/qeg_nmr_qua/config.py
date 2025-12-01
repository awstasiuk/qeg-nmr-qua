"""
OPX-1000 Configuration Module.

This module provides configuration utilities for the OPX-1000 LF-FEM
for solid state NMR experiments.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChannelConfig:
    """Configuration for an individual channel."""

    port: int
    offset: float = 0.0
    delay: float = 0.0


@dataclass
class PulseConfig:
    """Configuration for a pulse sequence element."""

    name: str
    length: int  # in nanoseconds
    amplitude: float = 1.0
    waveform: str = "const"


@dataclass
class OPXConfig:
    """
    Configuration class for OPX-1000 LF-FEM NMR experiments.

    This class provides a structured way to define and manage
    configuration parameters for the OPX-1000 low-frequency
    front-end module used in solid state NMR experiments.

    Attributes:
        host: IP address or hostname of the OPX-1000.
        port: Port number for the QOP connection.
        controller_name: Name of the OPX controller.
        fluorine_frequency: Resonance frequency for fluorine spins in Hz.
        channels: Dictionary of channel configurations.
        pulses: Dictionary of pulse configurations.
    """

    host: str = "127.0.0.1"
    port: int = 9510
    controller_name: str = "con1"
    fluorine_frequency: float = 376.5e6  # Typical 19F frequency at 9.4T
    channels: dict[str, ChannelConfig] = field(default_factory=dict)
    pulses: dict[str, PulseConfig] = field(default_factory=dict)

    def add_channel(
        self,
        name: str,
        port: int,
        offset: float = 0.0,
        delay: float = 0.0,
    ) -> None:
        """
        Add a channel configuration.

        Args:
            name: Name of the channel.
            port: Physical port number on the OPX.
            offset: DC offset voltage.
            delay: Time delay in nanoseconds.
        """
        self.channels[name] = ChannelConfig(port=port, offset=offset, delay=delay)

    def add_pulse(
        self,
        name: str,
        length: int,
        amplitude: float = 1.0,
        waveform: str = "const",
    ) -> None:
        """
        Add a pulse configuration.

        Args:
            name: Name of the pulse.
            length: Pulse length in nanoseconds.
            amplitude: Pulse amplitude (0.0 to 1.0).
            waveform: Type of waveform.
        """
        self.pulses[name] = PulseConfig(
            name=name, length=length, amplitude=amplitude, waveform=waveform
        )

    def to_qua_config(self) -> dict[str, Any]:
        """
        Convert configuration to QUA-compatible format.

        Returns:
            Dictionary containing the configuration in QUA format.
        """
        config: dict[str, Any] = {
            "version": 1,
            "controllers": {
                self.controller_name: {
                    "analog_outputs": {},
                    "analog_inputs": {},
                }
            },
            "elements": {},
            "pulses": {},
            "waveforms": {},
        }

        # Add channels as analog outputs
        for name, channel in self.channels.items():
            config["controllers"][self.controller_name]["analog_outputs"][channel.port] = {
                "offset": channel.offset,
                "delay": channel.delay,
            }

        # Add pulses
        for name, pulse in self.pulses.items():
            config["pulses"][name] = {
                "operation": "control",
                "length": pulse.length,
                "waveforms": {"single": f"{name}_wf"},
            }
            config["waveforms"][f"{name}_wf"] = {
                "type": "constant",
                "sample": pulse.amplitude,
            }

        return config
