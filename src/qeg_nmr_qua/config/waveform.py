from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Type, TypeVar, Literal


@dataclass
class AnalogWaveform:
    """
    Configuration for a single waveform.
    """

    wf_type: Literal["constant", "arbitrary"] = "constant"
    sample: float | list = (
        0.0  # amplitude value(s); float for constant, list for arbitrary
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.wf_type,
            "sample": self.sample,
        }


@dataclass
class DigitalWaveform:
    """
    Configuration for a digital waveform (marker). A length of 0 means the marker will hold its state
    for the duration of the pulse it is associated with. If the pulse ends, the marker returns to 0.
    """

    state: int = 0  # 0 or 1
    length: int = 0  # in nanoseconds

    def to_dict(self) -> Dict[str, str]:
        return {"samples": [(self.state, self.length)]}


@dataclass
class AnalogWaveformConfig:
    """
    Simple container for waveform name mappings, e.g. {"single": "const_wf"}.
    Keeps the mapping opaque so other parts of the code can use arbitrary keys.
    """

    waveforms: Dict[str, AnalogWaveform] = field(default_factory=dict)

    def add_waveform(
        self,
        name: str,
        wf_type: Literal["constant", "arbitrary"] = "constant",
        sample: float | list[float] = 0.0,
    ) -> None:
        """
        Add a waveform to the configuration for defining multiple pulse-types. Pulses are either constant amplitude
        or arbitrary waveforms. If constant, `sample` is a float amplitude value. If arbitrary, `sample` is a list of amplitude values
        which define the waveform shape, between -1 and 1.
        """
        self.waveforms[name] = AnalogWaveform(wf_type=wf_type, sample=sample)

    def to_dict(self) -> Dict[str, Any]:
        return {name: wf.to_dict() for name, wf in self.waveforms.items()}


@dataclass
class DigitalWaveformConfig:
    waveforms: Dict[str, DigitalWaveform] = field(default_factory=dict)

    def add_waveform(self, name: str, state: int = 0, length: int = 0) -> None:
        """
        Add a digital waveform (marker) to the configuration. A length of 0 means the marker will hold its state
        for the duration of the pulse it is associated with. If the pulse ends, the marker returns to 0.
        """
        self.waveforms[name] = DigitalWaveform(state=state, length=length)

    def to_dict(self) -> Dict[str, Any]:
        return {name: wf.to_dict() for name, wf in self.waveforms.items()}
