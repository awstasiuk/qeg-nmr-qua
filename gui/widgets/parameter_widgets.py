"""Custom parameter widgets for editing experiment settings."""

from pathlib import Path
from typing import Any, Callable, Optional

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QSpinBox, QPushButton, QFileDialog,
    QGroupBox, QScrollArea, QFormLayout
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPalette, QColor


class BaseParameterWidget(QWidget):
    """Base class for parameter editing widgets."""
    
    value_changed = pyqtSignal(object)  # Emits new value
    
    def __init__(self, label: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.label_text = label
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 2, 5, 2)
        
        self.label = QLabel(label)
        self.label.setMinimumWidth(150)
        if tooltip:
            self.label.setToolTip(tooltip)
        
        self.layout.addWidget(self.label)
    
    def get_value(self) -> Any:
        """Get the current value of the parameter."""
        raise NotImplementedError
    
    def set_value(self, value: Any):
        """Set the value of the parameter."""
        raise NotImplementedError
    
    def mark_invalid(self, invalid: bool = True):
        """Mark the widget as having an invalid value."""
        raise NotImplementedError


class IntParameterWidget(BaseParameterWidget):
    """Widget for editing integer parameters."""
    
    def __init__(self, label: str, default_value: int = 0, min_value: int = 0, 
                 max_value: int = 1000000, tooltip: str = "", suffix: str = "", parent=None):
        super().__init__(label, tooltip, parent)
        
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(min_value)
        self.spinbox.setMaximum(max_value)
        self.spinbox.setValue(default_value)
        self.spinbox.setMinimumWidth(150)
        
        if suffix:
            self.spinbox.setSuffix(f" {suffix}")
        
        self.spinbox.valueChanged.connect(self.value_changed.emit)
        
        self.layout.addWidget(self.spinbox)
        self.layout.addStretch()
    
    def get_value(self) -> int:
        return self.spinbox.value()
    
    def set_value(self, value: int):
        self.spinbox.setValue(value)
    
    def mark_invalid(self, invalid: bool = True):
        self.spinbox.setProperty("invalid", invalid)
        self.spinbox.style().unpolish(self.spinbox)
        self.spinbox.style().polish(self.spinbox)


class FloatParameterWidget(BaseParameterWidget):
    """Widget for editing floating-point parameters."""
    
    def __init__(self, label: str, default_value: float = 0.0, min_value: float = -1e9, 
                 max_value: float = 1e9, decimals: int = 6, tooltip: str = "", 
                 suffix: str = "", parent=None):
        super().__init__(label, tooltip, parent)
        
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setMinimum(min_value)
        self.spinbox.setMaximum(max_value)
        self.spinbox.setDecimals(decimals)
        self.spinbox.setValue(default_value)
        self.spinbox.setMinimumWidth(150)
        
        if suffix:
            self.spinbox.setSuffix(f" {suffix}")
        
        self.spinbox.valueChanged.connect(self.value_changed.emit)
        
        self.layout.addWidget(self.spinbox)
        self.layout.addStretch()
    
    def get_value(self) -> float:
        return self.spinbox.value()
    
    def set_value(self, value: float):
        self.spinbox.setValue(value)
    
    def mark_invalid(self, invalid: bool = True):
        self.spinbox.setProperty("invalid", invalid)
        self.spinbox.style().unpolish(self.spinbox)
        self.spinbox.style().polish(self.spinbox)


class StringParameterWidget(BaseParameterWidget):
    """Widget for editing string parameters."""
    
    def __init__(self, label: str, default_value: str = "", tooltip: str = "", 
                 placeholder: str = "", parent=None):
        super().__init__(label, tooltip, parent)
        
        self.line_edit = QLineEdit()
        self.line_edit.setText(default_value)
        self.line_edit.setMinimumWidth(150)
        
        if placeholder:
            self.line_edit.setPlaceholderText(placeholder)
        
        self.line_edit.textChanged.connect(self.value_changed.emit)
        
        self.layout.addWidget(self.line_edit)
        self.layout.addStretch()
    
    def get_value(self) -> str:
        return self.line_edit.text()
    
    def set_value(self, value: str):
        self.line_edit.setText(value)
    
    def mark_invalid(self, invalid: bool = True):
        self.line_edit.setProperty("invalid", invalid)
        self.line_edit.style().unpolish(self.line_edit)
        self.line_edit.style().polish(self.line_edit)


class PathParameterWidget(BaseParameterWidget):
    """Widget for editing file/directory path parameters."""
    
    def __init__(self, label: str, default_value: str = "", tooltip: str = "", 
                 is_directory: bool = True, parent=None):
        super().__init__(label, tooltip, parent)
        
        self.is_directory = is_directory
        
        self.line_edit = QLineEdit()
        self.line_edit.setText(default_value)
        self.line_edit.setMinimumWidth(200)
        self.line_edit.textChanged.connect(self.value_changed.emit)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse)
        
        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.browse_button)
        self.layout.addStretch()
    
    def _browse(self):
        """Open file/directory browser dialog."""
        current_path = self.line_edit.text()
        
        if self.is_directory:
            path = QFileDialog.getExistingDirectory(
                self, "Select Directory", current_path
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select File", current_path
            )
        
        if path:
            self.line_edit.setText(path)
    
    def get_value(self) -> str:
        return self.line_edit.text()
    
    def set_value(self, value: str):
        self.line_edit.setText(value)
    
    def mark_invalid(self, invalid: bool = True):
        self.line_edit.setProperty("invalid", invalid)
        self.line_edit.style().unpolish(self.line_edit)
        self.line_edit.style().polish(self.line_edit)


class ParameterGroup(QGroupBox):
    """
    A collapsible group of parameter widgets.
    
    Organizes related parameters into labeled, collapsible sections.
    """
    
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.setCheckable(False)
        
        self.form_layout = QFormLayout()
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(self.form_layout)
        
        self.widgets = {}
    
    def add_parameter_widget(self, key: str, widget: BaseParameterWidget):
        """
        Add a parameter widget to this group.
        
        Args:
            key: Unique identifier for this parameter
            widget: The parameter widget to add
        """
        self.form_layout.addRow(widget)
        self.widgets[key] = widget
    
    def get_values(self) -> dict:
        """Get all parameter values as a dictionary."""
        return {key: widget.get_value() for key, widget in self.widgets.items()}
    
    def set_values(self, values: dict):
        """Set parameter values from a dictionary."""
        for key, value in values.items():
            if key in self.widgets:
                self.widgets[key].set_value(value)
