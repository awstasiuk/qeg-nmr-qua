"""Model for managing ExperimentSettings with Qt integration."""

from pathlib import Path
from typing import Any, Dict

from PyQt6.QtCore import QObject, pyqtSignal

from qeg_nmr_qua.config.settings import ExperimentSettings


class SettingsModel(QObject):
    """
    Qt-friendly wrapper around ExperimentSettings.
    
    Provides signals for change notification and validation.
    """
    
    settings_changed = pyqtSignal()
    validation_error = pyqtSignal(str, str)  # field_name, error_message
    
    def __init__(self, settings: ExperimentSettings = None, parent=None):
        super().__init__(parent)
        self._settings = settings if settings is not None else ExperimentSettings()
        self._modified = False
    
    @property
    def settings(self) -> ExperimentSettings:
        """Get the underlying ExperimentSettings object."""
        return self._settings
    
    @property
    def is_modified(self) -> bool:
        """Check if settings have been modified."""
        return self._modified
    
    def get_value(self, key: str) -> Any:
        """Get a settings value by key."""
        return getattr(self._settings, key)
    
    def set_value(self, key: str, value: Any) -> bool:
        """
        Set a settings value by key with validation.
        
        Args:
            key: The settings attribute name
            value: The new value to set
            
        Returns:
            True if value was set successfully, False otherwise
        """
        try:
            # Validate the value
            if not self._validate_value(key, value):
                return False
            
            # Set the value
            setattr(self._settings, key, value)
            self._modified = True
            self.settings_changed.emit()
            return True
            
        except Exception as e:
            self.validation_error.emit(key, str(e))
            return False
    
    def _validate_value(self, key: str, value: Any) -> bool:
        """
        Validate a value for a given settings key.
        
        Args:
            key: The settings attribute name
            value: The value to validate
            
        Returns:
            True if valid, False otherwise (emits validation_error signal)
        """
        # Validation rules based on ExperimentSettings docstring
        
        if key == "n_avg":
            if not isinstance(value, int) or value < 1:
                self.validation_error.emit(key, "n_avg must be an integer >= 1")
                return False
        
        elif key == "pulse_length":
            if value < 64:
                self.validation_error.emit(key, "pulse_length must be >= 64 ns")
                return False
        
        elif key == "pulse_amplitude":
            if not (-0.5 <= value <= 0.5):
                self.validation_error.emit(key, "pulse_amplitude must be in range [-0.5, 0.5]")
                return False
        
        elif key == "readout_delay":
            if value < 5000:  # 5 µs in ns
                self.validation_error.emit(key, "readout_delay must be >= 5 µs")
                return False
        
        elif key == "center_freq" or key == "offset_freq":
            # Check IF frequency is in valid range
            center = self._settings.center_freq if key != "center_freq" else value
            offset = self._settings.offset_freq if key != "offset_freq" else value
            if_freq = center - offset
            
            if not (0 <= if_freq < 750e6):  # 750 MHz limit
                self.validation_error.emit(
                    key, 
                    f"IF frequency (center - offset) must be in range [0, 750 MHz], got {if_freq/1e6:.2f} MHz"
                )
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a dictionary."""
        return self._settings.to_dict()
    
    def from_dict(self, data: Dict[str, Any]):
        """Load settings from a dictionary."""
        self._settings = ExperimentSettings.from_dict(data)
        self._modified = False
        self.settings_changed.emit()
    
    def reset_modified(self):
        """Reset the modified flag."""
        self._modified = False
    
    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self._settings = ExperimentSettings()
        self._modified = True
        self.settings_changed.emit()
