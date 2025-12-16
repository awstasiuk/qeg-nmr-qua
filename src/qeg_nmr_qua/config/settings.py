from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional

from qualang_tools.units import unit

u = unit(coerce_to_integer=True)

UpdateCallback = Callable[["ExperimentSettings", Dict[str, Any]], None]


@dataclass
class ExperimentSettings:
    """
    Container for experiment-specific program parameters and hardware configuration.

    This dataclass manages all user-facing settings for NMR experiments on the OPX-1000,
    including pulse parameters, frequencies, readout configuration, and data handling.
    All values are stored in standard units (nanoseconds, Hz, amplitude) and converted internally
    as needed.

    **Features:**

    - **Mutable with validation**: Settings can be updated atomically with :meth:`update`
    - **Serialization**: Convert to/from dictionaries with :meth:`to_dict` and :meth:`from_dict`
    - **Change notifications**: Register callbacks with :meth:`register_update_callback` to
      be notified when settings change
    - **Atomic updates**: All changes are validated before being applied

    **Parameter Groups:**

    **Pulse Parameters**: Core pulse control settings

    - ``n_avg``: Number of signal averages (default: 4)
    - ``pulse_length``: Duration of control pulse in nanoseconds (default: 1.1 µs)
    - ``pulse_amplitude``: Normalized pulse amplitude 0-0.5 (default: 0.25, representing 0.5 Vpp)
    - ``rotation_angle``: Pulse rotation angle in degrees (default: 90°)

    **Continuous Wave (CW) Parameters**: For continuous wave experiments

    - ``const_len``: Length of continuous wave pulse in nanoseconds (default: 100 ns)
    - ``const_amp``: Amplitude of continuous wave pulse (default: 0.03)

    **Timing Parameters**: Experiment timing and delays

    - ``thermal_reset``: Pre-scan delay for thermal equilibration, in nanoseconds (default: 4 s)
    - ``readout_delay``: Minimum delay before measurement occurs, in nanoseconds (default: 20 µs)
    - ``dwell_time``: Demodulation interval during readout, in nanoseconds (default: 4 µs)
    - ``readout_start``: Start time of readout window, in nanoseconds (default: 0)
    - ``readout_end``: End time of readout window, in nanoseconds (default: 256 µs)

    **Frequency Parameters**: NMR frequency configuration

    - ``center_freq``: Center frequency for NMR in Hz (default: 282.1901 MHz for ¹⁹F)
    - ``offset_freq``: Frequency offset in Hz. This increases by 50-100 Hz every few days (default: 750 Hz)

    **Resonator Parameters**: Resonator excitation settings

    - ``readout_amp``: Readout pulse amplitude, should be small (default: 0.01)
    - ``excitation_length``: Duration of resonator excitation pulse in nanoseconds (default: 5 µs)
    - ``excitation_amp``: Amplitude of resonator excitation (default: 0.03)

    **Data Handling:**

    - ``save_dir``: Directory for saving experimental data (default: None, uses ``data/`` folder)

    **Configuration Keys**: Element names in the OPX configuration

    - ``res_key``: Resonator element name (default: "resonator")
    - ``amp_key``: Amplifier element name (default: "amplifier")
    - ``helper_key``: Helper element name (default: "helper")
    - ``sw_key``: Switch control element name (default: "switch")
    - ``pi_half_key``: π/2 pulse operation name (default: "pi_half")

    **Validation:**

    All settings are validated on instantiation and update:

    - ``n_avg`` must be an integer >= 1
    - ``pulse_length`` must be >= 64 ns
    - ``pulse_amplitude`` must be in range [-0.5, 0.5]
    - ``readout_delay`` must be >= 5 µs
    - Frequency must be in valid OPX range: 0 <= (center_freq - offset_freq) < 750 MHz
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
    excitation_length: int = 5 * u.us
    excitation_amp = 0.03

    # Data saving
    save_dir: Optional[Path | str] = None

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
        """Validate all current settings and raise ValueError if any are invalid.

        This method checks all constraints defined for ExperimentSettings:

        - ``n_avg`` must be a positive integer
        - ``pulse_length`` must be at least 64 ns (4 clock cycles @ 16 ns each)
        - ``pulse_amplitude`` must be in range [-0.5, 0.5] (max ±1 Vpp)
        - ``readout_delay`` must be at least 5 µs for ringdown protection
        - Effective frequency (center_freq - offset_freq) must be in OPX range [0, 750 MHz)
        - ``rotation_angle`` is normalized to [0, 360) automatically

        Raises:
            ValueError: If any setting violates the defined constraints.
        """
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
        """Update one or more settings atomically with full validation.

        All requested changes are validated together before any are applied,
        ensuring the settings object remains in a valid state even if update fails.
        Registered callbacks are invoked only if changes are actually made.

        **Thread Safety**: Not thread-safe. Callers must serialize access if concurrent
        updates are possible in their environment.

        Args:
            **kwargs: Field names and new values. Unknown fields raise AttributeError.

        Returns:
            dict: Dictionary of fields that actually changed (name -> new_value).
                  Empty dict if no changes were made or all new values matched existing ones.

        Raises:
            AttributeError: If an unknown setting name is provided.
            ValueError: If validation fails for any changed setting (no changes applied).

        Example:
            >>> settings = ExperimentSettings()
            >>> changes = settings.update(pulse_length=2000, n_avg=8)
            >>> # changes now contains {"pulse_length": 2000, "n_avg": 8}
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
        """Convert settings to a serializable dictionary.

        Returns all user-facing settings as a plain Python dict suitable for
        JSON serialization or storage. Internal fields (callbacks, locks, etc.)
        are excluded.

        Returns:
            dict: A shallow copy of all settings with internal fields excluded.

        See Also:
            :meth:`from_dict` to reconstruct settings from a dict.
        """
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
        """Create a new ExperimentSettings instance from a dictionary.

        Constructs a new instance with validation. Unknown fields in the input
        dict are silently ignored. All settings are validated before the instance
        is returned, ensuring consistency with class constraints.

        Args:
            data: Dictionary with setting names as keys. Can contain extra keys
                  which will be ignored.

        Returns:
            ExperimentSettings: A new validated instance.

        Raises:
            ValueError: If any settings in the dict violate validation constraints.
            TypeError: If any setting value is of an incompatible type.

        See Also:
            :meth:`to_dict` to convert an instance to a dict.

        Example:
            >>> data = {"n_avg": 16, "pulse_length": 2000, "extra_field": "ignored"}
            >>> settings = ExperimentSettings.from_dict(data)
        """
        # Only pass known fields to constructor
        allowed = {f.name for f in cls.__dataclass_fields__.values() if f.init}
        init_kwargs = {k: v for k, v in data.items() if k in allowed}
        inst = cls(**init_kwargs)  # type: ignore[arg-type]
        inst.validate()
        return inst

    def register_update_callback(self, fn: UpdateCallback) -> None:
        """Register a callback to be notified when settings change.

        The callback will be invoked each time settings are updated via :meth:`update`.
        The callback signature is ``fn(self, changes_dict)`` where ``changes_dict``
        contains the field names and new values.

        **Exception Handling**: Callback exceptions are caught and suppressed to
        prevent failures from propagating to the caller. Consider logging exceptions
        if needed.

        Args:
            fn: A callable with signature ``(self: ExperimentSettings, changes: Dict[str, Any]) -> None``.

        Raises:
            TypeError: If ``fn`` is not callable.

        See Also:
            :meth:`unregister_update_callback` to remove a callback.

        Example:
            >>> def on_settings_change(settings, changes):
            ...     print(f"Settings changed: {changes}")
            >>> settings = ExperimentSettings()
            >>> settings.register_update_callback(on_settings_change)
            >>> settings.update(n_avg=10)  # Prints: Settings changed: {'n_avg': 10}
        """
        if not callable(fn):
            raise TypeError("callback must be callable")
        if fn not in self._callbacks:
            self._callbacks.append(fn)

    def unregister_update_callback(self, fn: UpdateCallback) -> None:
        """Unregister a previously registered callback.

        Removes the callback from the list of callbacks to be invoked on updates.
        If the callback was not registered, this method does nothing (no error).

        Args:
            fn: The callback function to unregister. Must be the same object
                that was passed to :meth:`register_update_callback`.

        See Also:
            :meth:`register_update_callback` to register a callback.

        Example:
            >>> def on_change(settings, changes):
            ...     pass
            >>> settings = ExperimentSettings()
            >>> settings.register_update_callback(on_change)
            >>> settings.unregister_update_callback(on_change)
        """
        if fn in self._callbacks:
            self._callbacks.remove(fn)

    def _notify_update(self, changes: Dict[str, Any]) -> None:
        """Internal: Invoke all registered callbacks with change information.

        This is called automatically after successful updates and should not
        be called directly. Exceptions raised by callbacks are suppressed
        to avoid breaking caller code.

        Args:
            changes: Dictionary of field names to new values that changed.

        Note:
            This is an internal method and is not part of the public API.
        """
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
        """Create a shallow copy of these settings.

        Creates a new independent instance with the same field values.
        Callbacks are not copied (the new instance starts with no callbacks).
        Modifications to the copy do not affect the original.

        Returns:
            ExperimentSettings: A new instance with identical settings.

        Example:
            >>> settings1 = ExperimentSettings(n_avg=8)
            >>> settings2 = settings1.copy()
            >>> settings2.update(n_avg=16)
            >>> settings1.n_avg  # Still 8
            8
        """
        data = self.to_dict()
        return self.from_dict(data)

    def __repr__(self) -> str:
        fields = ", ".join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"{self.__class__.__name__}({fields})"

    def rf_freq(self) -> int:
        """Calculate the effective RF (radio frequency) in MHz.

        Computes the actual RF frequency used by the OPX by subtracting the
        frequency offset from the center frequency. This accounts for any
        frequency calibration adjustments stored in ``offset_freq``.

        Returns:
            int: The effective RF frequency in MHz.

        Example:
            >>> settings = ExperimentSettings(center_freq=282_190_100, offset_freq=75_000)
            >>> settings.rf_freq()
            282_115_100
        """
        return self.center_freq - self.offset_freq
