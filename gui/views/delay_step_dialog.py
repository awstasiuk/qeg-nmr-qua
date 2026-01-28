"""Dialog for adding/editing delay steps."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox,
    QDialogButtonBox, QComboBox, QLabel
)
from PyQt6.QtCore import Qt

from gui.models.sequence_step import DelayStep, StepType


class DelayStepDialog(QDialog):
    """Dialog for configuring delay parameters."""
    
    def __init__(self, parent=None, delay: DelayStep = None):
        super().__init__(parent)
        
        self.delay = delay
        self.setWindowTitle("Delay Configuration")
        self.setMinimumWidth(350)
        
        self._setup_ui()
        
        if delay:
            self._load_delay(delay)
    
    def _setup_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout(self)
        
        # Form layout
        form = QFormLayout()
        
        # Unit selector
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["nanoseconds (ns)", "microseconds (µs)", "milliseconds (ms)"])
        self.unit_combo.setCurrentIndex(1)  # Default to microseconds
        self.unit_combo.currentIndexChanged.connect(self._update_range)
        form.addRow("Time Unit:", self.unit_combo)
        
        # Duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 1000000)
        self.duration_spin.setValue(1)
        form.addRow("Duration:", self.duration_spin)
        
        # Info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #888; font-style: italic;")
        self.duration_spin.valueChanged.connect(self._update_info)
        form.addRow("", self.info_label)
        
        layout.addLayout(form)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self._update_range()
        self._update_info()
    
    def _update_range(self):
        """Update spin box range based on unit."""
        unit_index = self.unit_combo.currentIndex()
        
        if unit_index == 0:  # nanoseconds
            self.duration_spin.setRange(16, 1_000_000_000)
            self.duration_spin.setSuffix(" ns")
        elif unit_index == 1:  # microseconds
            self.duration_spin.setRange(1, 1_000_000)
            self.duration_spin.setSuffix(" µs")
        else:  # milliseconds
            self.duration_spin.setRange(1, 10000)
            self.duration_spin.setSuffix(" ms")
        
        self._update_info()
    
    def _update_info(self):
        """Update info label with converted duration."""
        duration_ns = self._get_duration_ns()
        
        # Show conversion
        if duration_ns >= 1_000_000:
            info = f"= {duration_ns / 1_000_000:.3f} ms"
        elif duration_ns >= 1_000:
            info = f"= {duration_ns / 1_000:.3f} µs"
        else:
            info = f"= {duration_ns} ns"
        
        self.info_label.setText(info)
    
    def _get_duration_ns(self) -> int:
        """Get duration in nanoseconds."""
        value = self.duration_spin.value()
        unit_index = self.unit_combo.currentIndex()
        
        if unit_index == 0:  # nanoseconds
            return value
        elif unit_index == 1:  # microseconds
            return value * 1_000
        else:  # milliseconds
            return value * 1_000_000
    
    def _load_delay(self, delay: DelayStep):
        """Load delay data into form."""
        duration_ns = delay.duration_ns
        
        # Choose appropriate unit
        if duration_ns >= 1_000_000 and duration_ns % 1_000_000 == 0:
            self.unit_combo.setCurrentIndex(2)  # milliseconds
            self.duration_spin.setValue(duration_ns // 1_000_000)
        elif duration_ns >= 1_000 and duration_ns % 1_000 == 0:
            self.unit_combo.setCurrentIndex(1)  # microseconds
            self.duration_spin.setValue(duration_ns // 1_000)
        else:
            self.unit_combo.setCurrentIndex(0)  # nanoseconds
            self.duration_spin.setValue(duration_ns)
    
    def get_delay_step(self) -> DelayStep:
        """Get the configured delay step."""
        return DelayStep(
            step_type=StepType.DELAY,
            duration_ns=self._get_duration_ns(),
        )
