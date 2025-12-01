from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Type, TypeVar, Literal
from qeg_nmr_qua.config.integration import IntegrationWeightMapping
from qeg_nmr_qua.config.waveform import PulseWaveforms


@dataclass
class ControlConfig:
    """
    Configuration for a control pulse. Does not currently support mixing waveforms.
    """

    operation: Literal["control", "measure"] = "control"
    length: int = 0  # in nanoseconds
    waveforms: str = "zero_wf"  # waveform name
    digital_marker: Literal["ON", "OFF"] = "OFF"  # set digital marker during pulse

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "length": self.length,
            "waveforms": {"single": self.waveforms},
            "digital_marker": self.digital_marker,
        }


@dataclass
class MeasConfig:
    """
    Configuration for a measurement. Does not support mixing waveforms.
    """

    operation: Literal["control", "measure"] = "measure"
    length: int  # in nanoseconds
    waveforms: str = "readout_wf"  # waveform name
    integration_weights: IntegrationWeightMapping = IntegrationWeightMapping()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation,
            "length": self.length,
            "waveforms": {"single": self.waveforms},
            "integration_weights": self.integration_weights.to_dict(),
        }


@dataclass
class PulsesConfig:
    """
    Configuration for a pulse, which can be either a control pulse or a measurement.
    """

    pulses: dict[str, ControlConfig | MeasConfig] = dataclass(
        field(default_factory=dict)
    )

    def add_control_pulse(
        self,
        name: str,
        length: int,
        waveform: str = "const",
        digital_marker: Literal["ON", "OFF"] = "OFF",
    ) -> None:
        """
        Add a control pulse configuration.

        Args:
            name: Name of the control pulse.
            length: Pulse length in nanoseconds.
            waveform: Waveform name.
            digital_marker: Whether to set the digital marker during the pulse.
        """
        self.pulses[name] = ControlConfig(
            operation="control",
            length=length,
            waveforms=waveform,
            digital_marker=digital_marker,
        )

    def add_measurement_pulse(
        self,
        name: str,
        length: int,
        waveform: str = "readout_wf",
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
        self.pulses[name] = MeasConfig(
            operation="measure",
            length=length,
            waveforms=waveform,
            integration_weights=integration_weights,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {self.name: self.config.to_dict()}
