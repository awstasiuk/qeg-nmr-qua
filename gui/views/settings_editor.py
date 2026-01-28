"""Settings editor widget for modifying experiment parameters."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QScrollArea, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

from qeg_nmr_qua.config.settings import ExperimentSettings
from gui.models.settings_model import SettingsModel
from gui.widgets.parameter_widgets import (
    ParameterGroup, IntParameterWidget, FloatParameterWidget,
    StringParameterWidget, PathParameterWidget
)


class SettingsEditor(QWidget):
    """
    Widget for editing ExperimentSettings with organized parameter groups.
    
    Provides validation, tooltips, and easy parameter management.
    """
    
    settings_updated = pyqtSignal(ExperimentSettings)
    
    def __init__(self, settings_model: SettingsModel = None, parent=None):
        super().__init__(parent)
        
        self.model = settings_model if settings_model is not None else SettingsModel()
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings_to_ui()
    
    def _setup_ui(self):
        """Create the user interface."""
        # Initialize param_widgets first
        self.param_widgets = {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create scroll area for parameter groups
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Create parameter groups
        self._create_pulse_parameters(scroll_layout)
        self._create_cw_parameters(scroll_layout)
        self._create_timing_parameters(scroll_layout)
        self._create_frequency_parameters(scroll_layout)
        self._create_resonator_parameters(scroll_layout)
        self._create_data_handling(scroll_layout)
        self._create_config_keys(scroll_layout)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.restore_button = QPushButton("Restore Defaults")
        self.restore_button.clicked.connect(self._restore_defaults)
        
        self.load_button = QPushButton("Load from File...")
        self.load_button.clicked.connect(self._load_from_file)
        
        self.save_button = QPushButton("Save to File...")
        self.save_button.clicked.connect(self._save_to_file)
        
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
    
    def _create_pulse_parameters(self, layout):
        """Create pulse parameter widgets."""
        group = ParameterGroup("Pulse Parameters")
        
        n_avg_widget = IntParameterWidget(
            "n_avg", 4, 1, 1000000,
            tooltip="Number of signal averages"
        )
        group.add_parameter_widget("n_avg", n_avg_widget)
        self.param_widgets["n_avg"] = n_avg_widget
        
        pulse_length_widget = IntParameterWidget(
            "pulse_length (ns)", 1100, 64, 10000000,
            tooltip="Duration of control pulse"
        )
        group.add_parameter_widget("pulse_length", pulse_length_widget)
        self.param_widgets["pulse_length"] = pulse_length_widget
        
        pulse_amp_widget = FloatParameterWidget(
            "pulse_amplitude", 0.25, -0.5, 0.5, 6,
            tooltip="Normalized pulse amplitude (0.5 = 1 Vpp)"
        )
        group.add_parameter_widget("pulse_amplitude", pulse_amp_widget)
        self.param_widgets["pulse_amplitude"] = pulse_amp_widget
        
        rotation_widget = FloatParameterWidget(
            "rotation_angle (°)", 90.0, 0.0, 360.0, 2,
            tooltip="Pulse rotation angle"
        )
        group.add_parameter_widget("rotation_angle", rotation_widget)
        self.param_widgets["rotation_angle"] = rotation_widget
        
        layout.addWidget(group)
    def _create_cw_parameters(self, layout):
        """Create continuous wave parameter widgets."""
        group = ParameterGroup("CW Parameters")
        
        const_len_widget = IntParameterWidget(
            "const_len (ns)", 100, 16, 1000000,
            tooltip="Length of continuous wave pulse"
        )
        group.add_parameter_widget("const_len", const_len_widget)
        self.param_widgets["const_len"] = const_len_widget
        
        const_amp_widget = FloatParameterWidget(
            "const_amp", 0.03, -0.5, 0.5, 6,
            tooltip="Amplitude of continuous wave pulse"
        )
        group.add_parameter_widget("const_amp", const_amp_widget)
        self.param_widgets["const_amp"] = const_amp_widget
        
        layout.addWidget(group)
    def _create_timing_parameters(self, layout):
        """Create timing parameter widgets."""
        group = ParameterGroup("Timing Parameters")
        
        thermal_widget = FloatParameterWidget(
            "thermal_reset (s)", 4.0, 0, 1e5, 3,
            tooltip="Pre-scan delay for thermal equilibration"
        )
        group.add_parameter_widget("thermal_reset", thermal_widget)
        self.param_widgets["thermal_reset"] = thermal_widget
        
        readout_delay_widget = FloatParameterWidget(
            "readout_delay (µs)", 20.0, 5, 1e6, 3,
            tooltip="Minimum delay before measurement"
        )
        group.add_parameter_widget("readout_delay", readout_delay_widget)
        self.param_widgets["readout_delay"] = readout_delay_widget
        
        dwell_widget = FloatParameterWidget(
            "dwell_time (µs)", 4.0, 0.016, 1000, 3,
            tooltip="Demodulation interval during readout"
        )
        group.add_parameter_widget("dwell_time", dwell_widget)
        self.param_widgets["dwell_time"] = dwell_widget
        
        readout_start_widget = FloatParameterWidget(
            "readout_start (µs)", 0.0, 0, 1e6, 3,
            tooltip="Start time of readout window"
        )
        group.add_parameter_widget("readout_start", readout_start_widget)
        self.param_widgets["readout_start"] = readout_start_widget
        
        readout_end_widget = FloatParameterWidget(
            "readout_end (µs)", 256.0, 0, 1e6, 3,
            tooltip="End time of readout window"
        )
        group.add_parameter_widget("readout_end", readout_end_widget)
        self.param_widgets["readout_end"] = readout_end_widget
        
        layout.addWidget(group)
    def _create_frequency_parameters(self, layout):
        """Create frequency parameter widgets."""
        group = ParameterGroup("Frequency Parameters")
        
        center_freq_widget = IntParameterWidget(
            "center_freq (Hz)", 282190100, 0, 1000000000,
            tooltip="Center frequency for NMR"
        )
        group.add_parameter_widget("center_freq", center_freq_widget)
        self.param_widgets["center_freq"] = center_freq_widget
        
        offset_freq_widget = IntParameterWidget(
            "offset_freq (Hz)", 750, -100000000, 100000000,
            tooltip="Frequency offset"
        )
        group.add_parameter_widget("offset_freq", offset_freq_widget)
        self.param_widgets["offset_freq"] = offset_freq_widget
        
        layout.addWidget(group)
    
    def _create_resonator_parameters(self, layout):
        """Create resonator parameter widgets."""
        group = ParameterGroup("Resonator Parameters")
        
        readout_amp_widget = FloatParameterWidget(
            "readout_amp", 0.01, 0.0, 0.5, 6,
            tooltip="Readout pulse amplitude (should be small)"
        )
        group.add_parameter_widget("readout_amp", readout_amp_widget)
        self.param_widgets["readout_amp"] = readout_amp_widget
        
        excitation_len_widget = IntParameterWidget(
            "excitation_length (ns)", 5000, 16, 1000000,
            tooltip="Duration of resonator excitation pulse"
        )
        group.add_parameter_widget("excitation_length", excitation_len_widget)
        self.param_widgets["excitation_length"] = excitation_len_widget
        
        excitation_amp_widget = FloatParameterWidget(
            "excitation_amp", 0.03, 0.0, 0.5, 6,
            tooltip="Amplitude of resonator excitation"
        )
        group.add_parameter_widget("excitation_amp", excitation_amp_widget)
        self.param_widgets["excitation_amp"] = excitation_amp_widget
        
        layout.addWidget(group)
    def _create_data_handling(self, layout):
        """Create data handling widgets."""
        group = ParameterGroup("Data Handling")
        
        save_dir_widget = PathParameterWidget(
            "save_dir", "",
            tooltip="Directory for saving experimental data",
            is_directory=True
        )
        group.add_parameter_widget("save_dir", save_dir_widget)
        self.param_widgets["save_dir"] = save_dir_widget
        
        layout.addWidget(group)
    
    def _create_config_keys(self, layout):
        """Create configuration key widgets."""
        group = ParameterGroup("Configuration Keys")
        
        res_key_widget = StringParameterWidget(
            "res_key", "resonator",
            tooltip="Resonator element name"
        )
        group.add_parameter_widget("res_key", res_key_widget)
        self.param_widgets["res_key"] = res_key_widget
        
        amp_key_widget = StringParameterWidget(
            "amp_key", "amplifier",
            tooltip="Amplifier element name"
        )
        group.add_parameter_widget("amp_key", amp_key_widget)
        self.param_widgets["amp_key"] = amp_key_widget
        
        helper_key_widget = StringParameterWidget(
            "helper_key", "helper",
            tooltip="Helper element name"
        )
        group.add_parameter_widget("helper_key", helper_key_widget)
        self.param_widgets["helper_key"] = helper_key_widget
        
        sw_key_widget = StringParameterWidget(
            "sw_key", "switch",
            tooltip="Switch control element name"
        )
        group.add_parameter_widget("sw_key", sw_key_widget)
        self.param_widgets["sw_key"] = sw_key_widget
        
        pi_half_key_widget = StringParameterWidget(
            "pi_half_key", "pi_half",
            tooltip="π/2 pulse operation name"
        )
        group.add_parameter_widget("pi_half_key", pi_half_key_widget)
        self.param_widgets["pi_half_key"] = pi_half_key_widget
        
        layout.addWidget(group)
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Connect all parameter widgets to validation
        for key, widget in self.param_widgets.items():
            widget.value_changed.connect(lambda value, k=key: self._on_value_changed(k, value))
        
        # Connect model signals
        self.model.validation_error.connect(self._on_validation_error)
        self.model.settings_changed.connect(self._on_settings_changed)
    
    def _load_settings_to_ui(self):
        """Load current settings from model into UI widgets."""
        settings = self.model.settings
        
        for key, widget in self.param_widgets.items():
            value = getattr(settings, key, None)
            if value is not None:
                if key == "save_dir" and value is not None:
                    widget.set_value(str(value))
                # Convert nanoseconds to user-facing units
                elif key == "thermal_reset":
                    widget.set_value(value / 1e9)  # ns to seconds
                elif key in ["readout_delay", "dwell_time", "readout_start", "readout_end"]:
                    widget.set_value(value / 1e3)  # ns to microseconds
                else:
                    widget.set_value(value)
    
    def _on_value_changed(self, key: str, value):
        """Handle parameter value changes."""
        # Convert save_dir to Path if needed
        if key == "save_dir" and value:
            value = Path(value) if value else None
        # Convert user-facing units back to nanoseconds
        elif key == "thermal_reset":
            value = int(value * 1e9)  # seconds to ns
        elif key in ["readout_delay", "dwell_time", "readout_start", "readout_end"]:
            value = int(value * 1e3)  # microseconds to ns
        
        # Attempt to set value in model (will validate)
        success = self.model.set_value(key, value)
        
        if success:
            # Clear invalid marking
            self.param_widgets[key].mark_invalid(False)
            self.settings_updated.emit(self.model.settings)
        else:
            # Mark as invalid
            self.param_widgets[key].mark_invalid(True)
    
    def _on_validation_error(self, field_name: str, error_message: str):
        """Handle validation errors from the model."""
        if field_name in self.param_widgets:
            self.param_widgets[field_name].mark_invalid(True)
    
    def _on_settings_changed(self):
        """Handle settings changes from the model."""
        self.settings_updated.emit(self.model.settings)
    
    def _restore_defaults(self):
        """Restore all settings to default values."""
        reply = QMessageBox.question(
            self, "Restore Defaults",
            "Are you sure you want to restore all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.model.reset_to_defaults()
            self._load_settings_to_ui()
    
    def _load_from_file(self):
        """Load settings from a JSON file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Settings", "", "JSON Files (*.json)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.model.from_dict(data)
                self._load_settings_to_ui()
                QMessageBox.information(self, "Success", "Settings loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load settings: {str(e)}")
    
    def _save_to_file(self):
        """Save current settings to a JSON file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Settings", "", "JSON Files (*.json)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(self.model.to_dict(), f, indent=2)
                QMessageBox.information(self, "Success", "Settings saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def get_settings(self) -> ExperimentSettings:
        """Get the current ExperimentSettings object."""
        return self.model.settings
    
    def set_settings(self, settings: ExperimentSettings):
        """Set new settings and update UI."""
        self.model._settings = settings
        self.model._modified = False
        self._load_settings_to_ui()
