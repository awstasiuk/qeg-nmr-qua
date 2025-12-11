from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional

from qualang_tools.units import unit

u = unit(coerce_to_integer=True)

UpdateCallback = Callable[["ExperimentSettings", Dict[str, Any]], None]


@dataclass
class ExperimentSettings:
    """
    Container for experiment-specific program parameters.

    This object is mutable and supports:
      - update(**kwargs): partial updates with validation
      - to_dict()/from_dict(): simple (de)serialization
      - register_update_callback(fn): notify external config managers when
        settings change (callback signature: fn(self, changes_dict))
    """

    # Core experiment parameters
    n_avg: int = 4
    pulse_length: int = 1.100 * u.us  # nanoseconds
    pulse_amplitude: float = 0.25  # 0.5*Vpp
    rotation_angle: float = 90.0  # degrees

    # cw params
    const_len: int = 100 * u.ns
    const_amp: float = 0.03

    # pre-scan delay
    thermal_reset: int = 4 * u.s

    # Frequencies
    center_freq: int = 282.1901 * u.MHz
    offset_freq: int = 750 * u.Hz

    # readout parameters
    readout_delay: int = 20 * u.us
    readout_amp: float = 0.01  # should be small
    dwell_time: int = 4 * u.us
    readout_start: int = 0 * u.us
    readout_end: int = 256 * u.us

    # resonator excitation
    excitation_len = 5 * u.us
    excitation_amp = 0.03

    # config element keys
    res_key: str = "resonator"
    amp_key: str = "amplifier"
    helper_key: str = "helper"
    sw_key: str = "switch"
    pi_half_key: str = "pi_half"

    # Internal: callbacks (no thread locking - updates are not synchronized)
    _callbacks: List[UpdateCallback] = field(
        default_factory=list, init=False, repr=False
    )

    def validate(self) -> None:
        """Validate current settings. Raise ValueError on invalid values."""
        if self.n_avg < 1 or not isinstance(self.n_avg, int):
            raise ValueError("n_avg must be an integer >= 1")
        if self.pulse_length < 16 * 4:
            raise ValueError("pulse length must be at least 64 ns")
        if abs(self.pulse_amplitude) > 0.5:
            raise ValueError("pulse power max at 1 Vpp")
        if self.readout_delay / u.us < 5:
            raise ValueError(
                "readout delay must be at least 5 us to protect from ringdown"
            )
        if (
            self.center_freq - self.offset_freq < 0
            or self.center_freq - self.offset_freq >= 750 * u.MHz
        ):
            raise ValueError(
                "Frequency out of OPX range. Ensure 0 <= center_freq - offset_freq < 750 MHz"
            )

        # Normalize rotation angle to [0, 360)
        self.rotation_angle = self.rotation_angle % 360.0

    def update(self, **kwargs) -> Dict[str, Any]:
        """
        Update one or more fields atomically with validation.

        Returns a dict of actually changed fields and their new values.
        Registered callbacks are invoked with (self, changes_dict).
        """
        if not kwargs:
            return {}

        # Create a tentative, serializable copy and apply updates for validation.
        # We do not perform thread synchronization here — callers must ensure
        # they coordinate access if concurrent updates are possible in their
        # environment.
        tentative = self.from_dict(self.to_dict())
        for k, v in kwargs.items():
            if not hasattr(tentative, k):
                raise AttributeError(f"Unknown setting: {k}")
            setattr(tentative, k, v)

        # Validate tentative values (this may normalize e.g. rotation_angle)
        tentative.validate()

        # Determine which fields changed and apply to self
        changes: Dict[str, Any] = {}
        for field_name, new_value in tentative.to_dict().items():
            old_value = getattr(self, field_name)
            if old_value != new_value:
                setattr(self, field_name, new_value)
                changes[field_name] = new_value

        if changes:
            self._notify_update(changes)
        return changes

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable dict of user-facing settings (no internals)."""
        # Build the dict directly from dataclass fields to avoid deep-copying
        # internal/unpicklable objects (e.g. threading.Lock) which `asdict`
        # may attempt to deepcopy and therefore fail.
        data: Dict[str, Any] = {}
        for name, f in self.__dataclass_fields__.items():
            if name in ("_callbacks", "_lock"):
                continue
            data[name] = getattr(self, name)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentSettings":
        """Create an instance from a dict. Validation is performed."""
        # Only pass known fields to constructor
        allowed = {f.name for f in cls.__dataclass_fields__.values() if f.init}
        init_kwargs = {k: v for k, v in data.items() if k in allowed}
        inst = cls(**init_kwargs)  # type: ignore[arg-type]
        inst.validate()
        return inst

    def register_update_callback(self, fn: UpdateCallback) -> None:
        """Register a callback called on changes: fn(self, changes_dict)."""
        if not callable(fn):
            raise TypeError("callback must be callable")
        if fn not in self._callbacks:
            self._callbacks.append(fn)

    def unregister_update_callback(self, fn: UpdateCallback) -> None:
        """Unregister a previously registered callback."""
        if fn in self._callbacks:
            self._callbacks.remove(fn)

    def _notify_update(self, changes: Dict[str, Any]) -> None:
        """Call registered callbacks with the changes. Exceptions are not propagated."""
        # Make a shallow copy to avoid mutation by callbacks
        callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(self, changes)
            except Exception:
                # Intentionally swallow exceptions to avoid breaking caller code.
                # In a real system, consider logging these.
                pass

    def copy(self) -> "ExperimentSettings":
        """Return a deep-ish copy (callbacks are not copied)."""
        data = self.to_dict()
        return self.from_dict(data)

    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({fields})"

    def rf_freq(self) -> int:
        """Compute the RF frequency as center_freq - offset_freq."""
        return self.center_freq - self.offset_freq
