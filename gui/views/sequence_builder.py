"""Sequence builder widget for constructing pulse sequences visually."""

from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from gui.models.sequence_step import SequenceStep, PulseStep, DelayStep, LoopStep, StepType


class SequenceBuilderWidget(QWidget):
    """
    Visual builder for creating pulse sequences.
    
    Provides tree view of sequence steps with add/edit/delete/reorder operations.
    """
    
    # Signals
    sequence_changed = pyqtSignal()
    sequence_valid = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.steps: List[SequenceStep] = []
        self._setup_ui()
        self._update_experiment_type()
    
    def _setup_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Experiment type indicator
        self.exp_type_label = QPushButton("1D Experiment")
        self.exp_type_label.setEnabled(False)
        self.exp_type_label.setStyleSheet("""
            QPushButton:disabled {
                background-color: #2d5d8f;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 3px;
            }
        """)
        header_layout.addWidget(self.exp_type_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Sequence tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Sequence Steps", "Details"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._edit_step)
        layout.addWidget(self.tree)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.add_pulse_btn = QPushButton("➕ Add Pulse")
        self.add_pulse_btn.clicked.connect(self._add_pulse)
        button_layout.addWidget(self.add_pulse_btn)
        
        self.add_delay_btn = QPushButton("⏱ Add Delay")
        self.add_delay_btn.clicked.connect(self._add_delay)
        button_layout.addWidget(self.add_delay_btn)
        
        self.add_loop_btn = QPushButton("🔁 Add Loop")
        self.add_loop_btn.clicked.connect(self._add_loop)
        button_layout.addWidget(self.add_loop_btn)
        
        button_layout.addStretch()
        
        self.clear_btn = QPushButton("🗑 Clear All")
        self.clear_btn.clicked.connect(self._clear_sequence)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # Reorder buttons
        reorder_layout = QHBoxLayout()
        
        self.move_up_btn = QPushButton("↑ Move Up")
        self.move_up_btn.clicked.connect(self._move_up)
        reorder_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("↓ Move Down")
        self.move_down_btn.clicked.connect(self._move_down)
        reorder_layout.addWidget(self.move_down_btn)
        
        self.delete_btn = QPushButton("❌ Delete")
        self.delete_btn.clicked.connect(self._delete_step)
        reorder_layout.addWidget(self.delete_btn)
        
        reorder_layout.addStretch()
        
        layout.addLayout(reorder_layout)
        
        self._update_tree()
    
    def _update_tree(self):
        """Update the tree view with current steps."""
        self.tree.clear()
        
        for i, step in enumerate(self.steps):
            self._add_step_to_tree(step, None, i)
        
        self._update_experiment_type()
    
    def _add_step_to_tree(self, step: SequenceStep, parent: Optional[QTreeWidgetItem], index: int):
        """Add a step to the tree."""
        item = QTreeWidgetItem(parent if parent else self.tree)
        
        # Set display text
        item.setText(0, f"{index + 1}. {step.get_display_name()}")
        
        # Set details
        details = self._get_step_details(step)
        item.setText(1, details)
        
        # Store step data
        item.setData(0, Qt.ItemDataRole.UserRole, step)
        
        # Style based on step type and state
        if not step.enabled:
            font = item.font(0)
            font.setStrikeOut(True)
            item.setFont(0, font)
            item.setForeground(0, QColor(128, 128, 128))
        
        if step.step_type == StepType.PULSE:
            item.setForeground(0, QColor(100, 200, 255))
        elif step.step_type == StepType.DELAY:
            item.setForeground(0, QColor(255, 200, 100))
        elif step.step_type == StepType.LOOP:
            item.setForeground(0, QColor(200, 255, 100))
            # Add nested steps
            if isinstance(step, LoopStep):
                for j, nested_step in enumerate(step.steps):
                    self._add_step_to_tree(nested_step, item, j)
                item.setExpanded(True)
    
    def _get_step_details(self, step: SequenceStep) -> str:
        """Get details string for a step."""
        if isinstance(step, PulseStep):
            parts = [step.element]
            if step.amplitude is not None:
                parts.append(f"amp={step.amplitude:.3f}")
            if step.phase is not None:
                parts.append(f"φ={step.phase}°")
            return ", ".join(parts)
        elif isinstance(step, DelayStep):
            return f"{step.duration_ns} ns"
        elif isinstance(step, LoopStep):
            return f"{step.iterations} iterations"
        return ""
    
    def _update_experiment_type(self):
        """Update the experiment type label based on sequence."""
        has_sweep = any(isinstance(s, PulseStep) and s.amplitude_sweep for s in self.steps)
        exp_type = "2D" if has_sweep else "1D"
        self.exp_type_label.setText(f"{exp_type} Experiment")
        
        # Update color
        if has_sweep:
            self.exp_type_label.setStyleSheet("""
                QPushButton:disabled {
                    background-color: #8f2d5d;
                    color: white;
                    font-weight: bold;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
            """)
        else:
            self.exp_type_label.setStyleSheet("""
                QPushButton:disabled {
                    background-color: #2d5d8f;
                    color: white;
                    font-weight: bold;
                    padding: 5px 10px;
                    border-radius: 3px;
                }
            """)
    
    def _add_pulse(self):
        """Add a new pulse step."""
        from gui.views.pulse_step_dialog import PulseStepDialog
        
        dialog = PulseStepDialog(self)
        if dialog.exec():
            pulse = dialog.get_pulse_step()
            self.steps.append(pulse)
            self._update_tree()
            self.sequence_changed.emit()
    
    def _add_delay(self):
        """Add a new delay step."""
        from gui.views.delay_step_dialog import DelayStepDialog
        
        dialog = DelayStepDialog(self)
        if dialog.exec():
            delay = dialog.get_delay_step()
            self.steps.append(delay)
            self._update_tree()
            self.sequence_changed.emit()
    
    def _add_loop(self):
        """Add a new loop step."""
        loop = LoopStep(step_type=StepType.LOOP, iterations=1)
        self.steps.append(loop)
        self._update_tree()
        self.sequence_changed.emit()
    
    def _edit_step(self, item: QTreeWidgetItem, column: int):
        """Edit the selected step."""
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if not step:
            return
        
        if isinstance(step, PulseStep):
            from gui.views.pulse_step_dialog import PulseStepDialog
            dialog = PulseStepDialog(self, step)
            if dialog.exec():
                updated_step = dialog.get_pulse_step()
                # Find and replace
                index = self.steps.index(step)
                self.steps[index] = updated_step
                self._update_tree()
                self.sequence_changed.emit()
        
        elif isinstance(step, DelayStep):
            from gui.views.delay_step_dialog import DelayStepDialog
            dialog = DelayStepDialog(self, step)
            if dialog.exec():
                updated_step = dialog.get_delay_step()
                index = self.steps.index(step)
                self.steps[index] = updated_step
                self._update_tree()
                self.sequence_changed.emit()
    
    def _delete_step(self):
        """Delete the selected step."""
        item = self.tree.currentItem()
        if not item:
            return
        
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step in self.steps:
            self.steps.remove(step)
            self._update_tree()
            self.sequence_changed.emit()
    
    def _move_up(self):
        """Move selected step up."""
        item = self.tree.currentItem()
        if not item:
            return
        
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step in self.steps:
            index = self.steps.index(step)
            if index > 0:
                self.steps[index], self.steps[index - 1] = self.steps[index - 1], self.steps[index]
                self._update_tree()
                self.sequence_changed.emit()
    
    def _move_down(self):
        """Move selected step down."""
        item = self.tree.currentItem()
        if not item:
            return
        
        step = item.data(0, Qt.ItemDataRole.UserRole)
        if step in self.steps:
            index = self.steps.index(step)
            if index < len(self.steps) - 1:
                self.steps[index], self.steps[index + 1] = self.steps[index + 1], self.steps[index]
                self._update_tree()
                self.sequence_changed.emit()
    
    def _clear_sequence(self):
        """Clear all steps."""
        if self.steps:
            reply = QMessageBox.question(
                self, "Clear Sequence",
                "Are you sure you want to clear all steps?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.steps.clear()
                self._update_tree()
                self.sequence_changed.emit()
    
    def _show_context_menu(self, pos):
        """Show context menu for tree items."""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self._edit_step(item, 0))
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self._delete_step)
        
        menu.addSeparator()
        
        move_up_action = menu.addAction("Move Up")
        move_up_action.triggered.connect(self._move_up)
        
        move_down_action = menu.addAction("Move Down")
        move_down_action.triggered.connect(self._move_down)
        
        menu.exec(self.tree.mapToGlobal(pos))
    
    def get_steps(self) -> List[SequenceStep]:
        """Get the current sequence steps."""
        return self.steps.copy()
    
    def set_steps(self, steps: List[SequenceStep]):
        """Set the sequence steps."""
        self.steps = steps.copy()
        self._update_tree()
        self.sequence_changed.emit()
    
    def clear(self):
        """Clear all steps without confirmation."""
        self.steps.clear()
        self._update_tree()
        self.sequence_changed.emit()
