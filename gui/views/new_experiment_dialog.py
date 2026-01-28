"""Dialog for creating new experiments."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt


class NewExperimentDialog(QDialog):
    """
    Dialog for creating a new experiment.
    
    Prompts user for:
    - Experiment name/prefix
    - Experiment type (1D, 2D, Custom)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Experiment")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the user interface."""
        main_layout = QVBoxLayout(self)
        
        # Experiment info group
        info_group = QGroupBox("Experiment Details")
        form_layout = QFormLayout()
        
        # Name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., 'calibration' or 'fid_sweep'")
        form_layout.addRow("Experiment Name:", self.name_input)
        
        # Type selector
        self.type_combo = QComboBox()
        self.type_combo.addItems(["1D", "2D", "Custom"])
        form_layout.addRow("Experiment Type:", self.type_combo)
        
        info_group.setLayout(form_layout)
        main_layout.addWidget(info_group)
        
        # Description
        description = QLabel(
            "A new experiment folder will be created with the format:\n"
            "<prefix>_0001, <prefix>_0002, etc.\n\n"
            "Current settings will be used as defaults."
        )
        description.setStyleSheet("color: #888888; font-size: 9pt;")
        main_layout.addWidget(description)
        
        # Button bar
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Create")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
    
    def get_name(self) -> str:
        """Get the experiment name/prefix."""
        return self.name_input.text().strip()
    
    def get_type(self) -> str:
        """Get the experiment type."""
        return self.type_combo.currentText()
    
    def get_values(self) -> dict:
        """Get all input values as a dictionary."""
        return {
            "name": self.get_name(),
            "type": self.get_type(),
        }
    
    def is_valid(self) -> bool:
        """Check if the input is valid."""
        name = self.get_name()
        
        if not name:
            return False
        
        # Check for valid characters (alphanumeric, underscore, hyphen)
        if not all(c.isalnum() or c in '_-' for c in name):
            return False
        
        # Don't allow names ending in numbers (reserved for auto-numbering)
        if name[-1].isdigit():
            return False
        
        return True
