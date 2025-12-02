from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Type, TypeVar, Literal
from qeg_nmr_qua.config.integration import IntegrationWeightMapping


@dataclass
class ControlPulse:
    """
    Configuration for a control pulse. Does not currently support mixing waveforms.
    """

    length: int = 0  # in nanoseconds
    waveforms: str = "zero_wf"  # waveform name
    digital_marker: Literal["ON", "OFF"] | None = (
        "OFF"  # set digital marker during pulse
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": "control",
            "length": self.length,
            "waveforms": {"single": self.waveforms},
            "digital_marker": self.digital_marker,
        }


@dataclass
class MeasPulse:
    """
    Configuration for a measurement. Does not support mixing waveforms.
    """

    length: int = 1000  # in nanoseconds
    waveforms: str = "readout_wf"  # waveform name
    integration_weights: IntegrationWeightMapping = field(
        default_factory=IntegrationWeightMapping
    )
    digital_marker: Literal["ON", "OFF"] | None = (
        None  # set digital marker during pulse
    )

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "operation": "measure",
            "length": self.length,
            "waveforms": {"single": self.waveforms},
            "integration_weights": self.integration_weights.to_dict(),
        }
        if self.digital_marker is not None:
            dct["digital_marker"] = self.digital_marker
        return dct


@dataclass
class PulseConfig:
    """
    Configuration for a pulse, which can be either a control pulse or a measurement.
    """

    pulses: dict[str, ControlPulse | MeasPulse] = field(default_factory=dict)

    def add_pulse(
        self,
        name: str,
        pulse: ControlPulse | MeasPulse,
    ) -> None:
        """
        Add a pulse configuration from one of the pulse types.

        Args:
            name: Name of the pulse.
            pulse: ControlPulse or MeasPulse instance.
        """
        self.pulses[name] = pulse

    def add_control_pulse(
        self,
        name: str,
        length: int,
        waveform: str = "const",
        digital_marker: Literal["ON", "OFF"] | None = "OFF",
    ) -> None:
        """
        Add a control pulse configuration.

        Args:
            name: Name of the control pulse.
            length: Pulse length in nanoseconds.
            waveform: Waveform name.
            digital_marker: Whether to set the digital marker during the pulse.
        """
        self.pulses[name] = ControlPulse(
            length=length,
            waveforms=waveform,
            digital_marker=digital_marker,
        )

    def add_measurement_pulse(
        self,
        name: str,
        length: int,
        waveform: str = "readout_wf",
        digital_marker: Literal["ON", "OFF"] | None = None,
        integration_weights: IntegrationWeightMapping = IntegrationWeightMapping(),
    ) -> None:
        """
        Add a measurement pulse configuration.

        Args:
            name: Name of the measurement pulse.
            length: Pulse length in nanoseconds.
            waveform: Waveform name.
            integration_weights: Integration weight mapping.
        """
        self.pulses[name] = MeasPulse(
            length=length,
            waveforms=waveform,
            integration_weights=integration_weights,
            digital_marker=digital_marker,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {name: pulse.to_dict() for name, pulse in self.pulses.items()}
