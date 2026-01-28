"""Dialog for adding/editing pulse steps."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDoubleSpinBox,
    QSpinBox, QCheckBox, QDialogButtonBox, QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt

from gui.models.sequence_step import PulseStep, StepType


class PulseStepDialog(QDialog):
    """Dialog for configuring pulse parameters."""
    
    def __init__(self, parent=None, pulse: PulseStep = None):
        super().__init__(parent)
        
        self.pulse = pulse
        self.setWindowTitle("Pulse Configuration")
        self.setMinimumWidth(400)
        
        self._setup_ui()
        
        if pulse:
            self._load_pulse(pulse)
    
    def _setup_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout(self)
        
        # Form layout for basic parameters
        form = QFormLayout()
        
        # Pulse name
        self.pulse_name_combo = QComboBox()
        self.pulse_name_combo.addItems([
            "pi_half", "pi", "pi_half_x", "pi_half_y",
            "pi_x", "pi_y", "pi_half_minus_x", "pi_half_minus_y"
        ])
        self.pulse_name_combo.setEditable(True)
        form.addRow("Pulse Name:", self.pulse_name_combo)
        
        # Element
        self.element_edit = QLineEdit("resonator")
        form.addRow("Element:", self.element_edit)
        
        # Amplitude
        self.amplitude_spin = QDoubleSpinBox()
        self.amplitude_spin.setRange(-0.5, 0.5)
        self.amplitude_spin.setDecimals(4)
        self.amplitude_spin.setSingleStep(0.01)
        self.amplitude_spin.setSpecialValueText("Use Default")
        self.amplitude_spin.setValue(self.amplitude_spin.minimum())
        form.addRow("Amplitude:", self.amplitude_spin)
        
        # Phase
        self.phase_spin = QDoubleSpinBox()
        self.phase_spin.setRange(-360, 360)
        self.phase_spin.setDecimals(2)
        self.phase_spin.setSingleStep(10)
        self.phase_spin.setSpecialValueText("Default")
        self.phase_spin.setValue(self.phase_spin.minimum())
        form.addRow("Phase (°):", self.phase_spin)
        
        layout.addLayout(form)
        
        # Sweep parameters group
        sweep_group = QGroupBox("2D Sweep Parameters")
        sweep_layout = QFormLayout()
        
        self.sweep_check = QCheckBox("Enable amplitude sweep (2D)")
        self.sweep_check.toggled.connect(self._toggle_sweep)
        sweep_layout.addRow(self.sweep_check)
        
        self.sweep_start_spin = QDoubleSpinBox()
        self.sweep_start_spin.setRange(0, 2.0)
        self.sweep_start_spin.setDecimals(3)
        self.sweep_start_spin.setValue(0.5)
        self.sweep_start_spin.setEnabled(False)
        sweep_layout.addRow("Start:", self.sweep_start_spin)
        
        self.sweep_end_spin = QDoubleSpinBox()
        self.sweep_end_spin.setRange(0, 2.0)
        self.sweep_end_spin.setDecimals(3)
        self.sweep_end_spin.setValue(1.5)
        self.sweep_end_spin.setEnabled(False)
        sweep_layout.addRow("End:", self.sweep_end_spin)
        
        self.sweep_points_spin = QSpinBox()
        self.sweep_points_spin.setRange(2, 1000)
        self.sweep_points_spin.setValue(50)
        self.sweep_points_spin.setEnabled(False)
        sweep_layout.addRow("Points:", self.sweep_points_spin)
        
        sweep_group.setLayout(sweep_layout)
        layout.addWidget(sweep_group)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _toggle_sweep(self, enabled: bool):
        """Toggle sweep parameter inputs."""
        self.sweep_start_spin.setEnabled(enabled)
        self.sweep_end_spin.setEnabled(enabled)
        self.sweep_points_spin.setEnabled(enabled)
    
    def _load_pulse(self, pulse: PulseStep):
        """Load pulse data into form."""
        # Find and set pulse name
        index = self.pulse_name_combo.findText(pulse.pulse_name)
        if index >= 0:
            self.pulse_name_combo.setCurrentIndex(index)
        else:
            self.pulse_name_combo.setCurrentText(pulse.pulse_name)
        
        self.element_edit.setText(pulse.element)
        
        if pulse.amplitude is not None:
            self.amplitude_spin.setValue(pulse.amplitude)
        
        if pulse.phase is not None:
            self.phase_spin.setValue(pulse.phase)
        
        if pulse.amplitude_sweep:
            self.sweep_check.setChecked(True)
            self.sweep_start_spin.setValue(pulse.sweep_start)
            self.sweep_end_spin.setValue(pulse.sweep_end)
            self.sweep_points_spin.setValue(pulse.sweep_points)
    
    def get_pulse_step(self) -> PulseStep:
        """Get the configured pulse step."""
        amplitude = None
        if self.amplitude_spin.value() > self.amplitude_spin.minimum():
            amplitude = self.amplitude_spin.value()
        
        phase = None
        if self.phase_spin.value() > self.phase_spin.minimum():
            phase = self.phase_spin.value()
        
        return PulseStep(
            step_type=StepType.PULSE,
            pulse_name=self.pulse_name_combo.currentText(),
            element=self.element_edit.text(),
            amplitude=amplitude,
            phase=phase,
            amplitude_sweep=self.sweep_check.isChecked(),
            sweep_start=self.sweep_start_spin.value(),
            sweep_end=self.sweep_end_spin.value(),
            sweep_points=self.sweep_points_spin.value(),
        )
