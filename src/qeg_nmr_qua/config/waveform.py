from dataclasses import dataclass, field
from collections.abc import Iterable
from typing import Dict, Optional, Any, Type, TypeVar, Literal


@dataclass
class AnalogWaveform:
    """
    Configuration for a single waveform.
    """

    sample: float | list = (
        0.0  # amplitude value(s); float for constant, list for arbitrary
    )

    def to_dict(self) -> Dict[str, Any]:
        """It may be better to link to a file when sample is an array."""
        return {
            "sample": self.sample,
        }

    def to_opx_config(self) -> Dict[str, Any]:
        return {"type": "constant", "sample": self.sample}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnalogWaveform":
        return cls(sample=d.get("sample", 0.0))

    def __repr__(self) -> str:
        sample_desc = (
            f"awg_len={len(self.sample)}"
            if isinstance(self.sample, (list, tuple))
            else f"amp={self.sample} V"
        )
        return f"<AnalogWaveform {sample_desc}>"


@dataclass
class ArbitraryWaveform:
    """
    Configuration for an arbitrary waveform.
    """

    samples: list[float] = field(default_factory=list)  # list of amplitude values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "samples": self.samples,
        }

    def to_opx_config(self) -> Dict[str, Any]:
        return {"type": "arbitrary", "samples": self.samples}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ArbitraryWaveform":
        return cls(samples=d.get("samples", []))

    def __repr__(self) -> str:
        return f"<ArbitraryWaveform len={len(self.samples)}>"


@dataclass
class DigitalWaveform:
    """
    Configuration for a digital waveform (marker). A length of 0 means the marker will hold its state
    for the duration of the pulse it is associated with. If the pulse ends, the marker returns to 0.
    """

    state: int = 0  # 0 or 1
    length: int = 0  # in nanoseconds

    def to_opx_config(self) -> Dict[str, str]:
        return {"samples": [(self.state, self.length)]}

    def to_dict(self) -> Dict[str, str]:
        return {
            "state": self.state,
            "length": self.length,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DigitalWaveform":
        return cls(state=d.get("state", 0), length=d.get("length", 0))

    def __repr__(self) -> str:
        return f"<DigitalWaveform state={self.state} length={self.length}>"


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
        sample: float | list[float] = 0.0,
    ) -> None:
        """
        Add a waveform to the configuration for defining multiple pulse-types. Pulses are either constant amplitude
        or arbitrary waveforms. If constant, `sample` is a float amplitude value. If arbitrary, `sample` is a list of amplitude values
        which define the waveform shape, between -1 and 1.
        """
        if isinstance(sample, Iterable):
            self.waveforms[name] = ArbitraryWaveform(samples=sample)
        else:
            self.waveforms[name] = AnalogWaveform(sample=sample)

    def to_dict(self) -> Dict[str, Any]:
        return {name: wf.to_dict() for name, wf in self.waveforms.items()}

    def to_opx_config(self) -> Dict[str, Any]:
        return {name: wf.to_opx_config() for name, wf in self.waveforms.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnalogWaveformConfig":
        awc = cls()
        for name, wd in (d or {}).items():
            if isinstance(wd, dict):
                awc.waveforms[name] = AnalogWaveform.from_dict(wd)
        return awc

    def __repr__(self) -> str:
        return f"<AnalogWaveformConfig waveforms={len(self.waveforms)}>"


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

    def to_opx_config(self) -> Dict[str, Any]:
        return {name: wf.to_opx_config() for name, wf in self.waveforms.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DigitalWaveformConfig":
        dwc = cls()
        for name, wd in (d or {}).items():
            if isinstance(wd, dict):
                dwc.waveforms[name] = DigitalWaveform.from_dict(wd)
        return dwc

    def __repr__(self) -> str:
        return f"<DigitalWaveformConfig waveforms={len(self.waveforms)}>"
