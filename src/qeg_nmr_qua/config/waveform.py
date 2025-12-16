from dataclasses import dataclass, field
from collections.abc import Iterable
from typing import Dict, Optional, Any, Type, TypeVar, Literal


@dataclass
class AnalogWaveform:
    """Configuration for a single analog waveform.

    Represents a waveform that can be output on an analog channel. Supports both
    constant-amplitude waveforms and arbitrary waveforms with sample-by-sample
    amplitude specification.

    Attributes:
        sample (float | list): Waveform amplitude specification.
            - If float: Constant waveform with that amplitude (in volts)
            - If list: Arbitrary waveform with per-sample amplitudes (in volts)
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
    """Configuration for an arbitrary (custom) analog waveform.

    Represents a shaped waveform defined sample-by-sample. Useful for complex
    pulse shapes like STIRAP, RAPID, or other optimal control pulses.

    Attributes:
        samples (list[float]): List of amplitude values (in volts) for each sample.
            The waveform is played back in sequence at the OPX sampling rate.
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
    """Configuration for a digital marker waveform.

    Defines a digital (binary) signal that can be used for RF switching, trigger
    signals, or monitoring pulse execution. The marker holds its specified state
    for the specified duration, then returns to 0 when the pulse ends.

    **Timing Behavior:**

    - Length 0: Marker holds its state for the entire duration of the associated pulse
    - Length > 0: Marker holds its state for the specified nanoseconds, then returns to 0

    Attributes:
        state (int): Digital state (0 or 1). 0 = low/off, 1 = high/on (default: 0).
        length (int): Duration the marker holds its state in nanoseconds (default: 0).
            Special case: 0 means hold for entire pulse duration.
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
    """Container for analog waveform definitions.

    Manages a collection of named analog waveforms. Waveforms are referenced by
    name in pulse configurations. This design allows arbitrary key names for
    maximum flexibility.

    **Waveform Types:**

    Waveforms can be:

    - Constant amplitude (flat pulse)
    - Arbitrary shaped (custom pulse envelope)

    Attributes:
        waveforms (Dict[str, AnalogWaveform]): Mapping of waveform names to
            their configurations. Example: {"pi_pulse": AnalogWaveform(...)}.
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
