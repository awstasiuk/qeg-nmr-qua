from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Type, TypeVar, Literal
from qeg_nmr_qua.config.integration import IntegrationWeightMapping


@dataclass
class ControlPulse:
    """
    Configuration for a control pulse. Does not currently support mixing waveforms.
    """

    length: int = 0  # in nanoseconds
    waveform: str = "zero_wf"  # waveform name
    digital_marker: Literal["ON", "OFF"] | None = (
        "OFF"  # set digital marker during pulse
    )

    def to_opx_config(self) -> Dict[str, Any]:
        return {
            "operation": "control",
            "length": self.length,
            "waveforms": {"single": self.waveform},
            "digital_marker": self.digital_marker,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "control",
            "length": self.length,
            "waveform": self.waveform,
            "digital_marker": self.digital_marker,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ControlPulse":
        return cls(
            length=d.get("length", 0),
            waveform=d.get("waveform", "zero_wf"),
            digital_marker=d.get("digital_marker", "OFF"),
        )

    def __repr__(self) -> str:
        return f"<ControlPulse len={self.length} wf={self.waveform} marker={self.digital_marker}>"


@dataclass
class MeasPulse:
    """
    Configuration for a measurement. Does not support mixing waveforms.
    """

    length: int = 1000  # in nanoseconds
    waveform: str = "readout_wf"  # waveform name
    integration_weights: IntegrationWeightMapping = field(
        default_factory=IntegrationWeightMapping
    )
    digital_marker: Literal["ON", "OFF"] | None = (
        None  # set digital marker during pulse
    )

    def to_opx_config(self) -> Dict[str, Any]:
        dct = {
            "operation": "measure",
            "length": self.length,
            "waveforms": {"single": self.waveform},
            "integration_weights": self.integration_weights.to_opx_config(),
        }
        if self.digital_marker is not None:
            dct["digital_marker"] = self.digital_marker
        return dct

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "measure",
            "length": self.length,
            "waveform": self.waveform,
            "integration_weights": self.integration_weights.to_dict(),
            "digital_marker": self.digital_marker,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MeasPulse":
        from qeg_nmr_qua.config.integration import IntegrationWeightMapping

        iw = IntegrationWeightMapping()
        if isinstance(d.get("integration_weights"), dict):
            vals = d.get("integration_weights", {})
            iw = IntegrationWeightMapping()
            for k, v in vals.items():
                if hasattr(iw, k):
                    setattr(iw, k, v)

        return cls(
            length=d.get("length", 1000),
            waveforms=d.get("waveforms", "readout_wf"),
            integration_weights=iw,
            digital_marker=d.get("digital_marker"),
        )

    def __repr__(self) -> str:
        # integration_weights may be an IntegrationWeights (has .weights) or a
        # IntegrationWeightMapping (has .to_dict()). Be robust.
        try:
            n = len(self.integration_weights.weights)
        except Exception:
            try:
                n = len(self.integration_weights.to_dict())
            except Exception:
                n = 0
        iw_summary = f"weights={n}"
        return f"<MeasPulse len={self.length} wf={self.waveforms} {iw_summary} marker={self.digital_marker}>"


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

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PulseConfig":
        pc = cls()
        for name, pd in d.items():
            if not isinstance(pd, dict):
                continue
            ptype = pd.get("type")
            if ptype == "control":
                pulse = ControlPulse.from_dict(pd)
            elif ptype == "measure" or ptype == "measurement":
                pulse = MeasPulse.from_dict(pd)
            else:
                pulse = ControlPulse.from_dict(pd)
            pc.pulses[name] = pulse
        return pc

    def __repr__(self) -> str:
        return f"<PulseConfig pulses={len(self.pulses)}>"

    def to_opx_config(self) -> Dict[str, Any]:
        return {name: pulse.to_opx_config() for name, pulse in self.pulses.items()}
