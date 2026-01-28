"""Experiment browser widget for navigating saved experiments."""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QMenu, QMessageBox, QPushButton, QInputDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

from gui.models.experiment_browser_model import ExperimentBrowserModel
from gui.models.experiment_metadata import ExperimentMetadata


class ExperimentBrowser(QWidget):
    """
    Browser widget for exploring saved experiments.
    
    Displays experiments in a tree structure with metadata preview and
    context menu for common operations.
    """
    
    # Signals
    experiment_selected = pyqtSignal(object)  # ExperimentMetadata or None
    experiment_double_clicked = pyqtSignal(ExperimentMetadata)
    experiment_deleted = pyqtSignal(str)
    
    def __init__(self, root_data_folder: Path = None, parent=None):
        super().__init__(parent)
        
        self.model = ExperimentBrowserModel(root_data_folder or Path("data"))
        self.current_metadata: ExperimentMetadata = None
        
        self._setup_ui()
        self._connect_signals()
        self._populate_tree()
    
    def _setup_ui(self):
        """Create the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header with refresh button
        header_layout = QHBoxLayout()
        
        title = QLabel("Experiments")
        font = title.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        title.setFont(font)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.refresh_button = QPushButton("↻ Refresh")
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.clicked.connect(self._refresh)
        header_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(header_layout)
        
        # Tree widget for experiments
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Experiments"])
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setColumnCount(1)
        self.tree.setMinimumHeight(200)
        
        main_layout.addWidget(self.tree)
        
        # Info panel
        self.info_label = QLabel("Select an experiment to view details")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #888888; font-style: italic;")
        
        main_layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """Connect model signals."""
        self.model.experiments_updated.connect(self._populate_tree)
        self.model.error_occurred.connect(self._show_error)
    
    def _populate_tree(self):
        """Populate the tree with experiments."""
        self.tree.clear()
        
        experiments = self.model.get_experiments()
        
        if not experiments:
            item = QTreeWidgetItem(["No experiments found"])
            item.setForeground(0, QColor("#888888"))
            self.tree.addTopLevelItem(item)
            return
        
        # Group experiments by prefix
        groups = {}
        for exp in experiments:
            # Extract prefix (everything before the last underscore and digits)
            parts = exp.name.rsplit('_', 1)
            prefix = parts[0] if len(parts) > 1 else exp.name
            
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(exp)
        
        # Create tree structure
        for prefix in sorted(groups.keys(), reverse=True):
            group_item = QTreeWidgetItem([prefix])
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            for exp in groups[prefix]:
                exp_item = QTreeWidgetItem([exp.display_name])
                exp_item.setData(0, Qt.ItemDataRole.UserRole, exp)
                
                # Add sub-items for metadata
                type_item = QTreeWidgetItem([f"Type: {exp.experiment_type}"])
                type_font = type_item.font(0)
                type_font.setWeight(QFont.Weight.Light)
                type_item.setFont(0, type_font)
                exp_item.addChild(type_item)
                
                avg_item = QTreeWidgetItem([f"Averages: {exp.n_avg}"])
                avg_font = avg_item.font(0)
                avg_font.setWeight(QFont.Weight.Light)
                avg_item.setFont(0, avg_font)
                exp_item.addChild(avg_item)
                
                group_item.addChild(exp_item)
            
            self.tree.addTopLevelItem(group_item)
            group_item.setExpanded(True)
    
    def _on_selection_changed(self):
        """Handle experiment selection."""
        items = self.tree.selectedItems()
        
        if not items:
            self.current_metadata = None
            self.info_label.setText("Select an experiment to view details")
            self.experiment_selected.emit(None)
            return
        
        item = items[0]
        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        
        if metadata and isinstance(metadata, ExperimentMetadata):
            self.current_metadata = metadata
            self._update_info_panel(metadata)
            self.experiment_selected.emit(metadata)
        else:
            self.current_metadata = None
            self.info_label.setText("")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on experiment."""
        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        
        if metadata and isinstance(metadata, ExperimentMetadata):
            self.experiment_double_clicked.emit(metadata)
    
    def _update_info_panel(self, metadata: ExperimentMetadata):
        """Update the info panel with experiment details."""
        info_text = "<b>" + metadata.display_name + "</b><br><br>"
        
        for key, value in metadata.info_dict.items():
            info_text += f"<b>{key}:</b> {value}<br>"
        
        self.info_label.setText(info_text)
    
    def _show_context_menu(self, position):
        """Show context menu for experiment operations."""
        item = self.tree.itemAt(position)
        metadata = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        
        if not metadata or not isinstance(metadata, ExperimentMetadata):
            return
        
        menu = QMenu()
        
        open_action = menu.addAction("Open Experiment")
        open_action.triggered.connect(
            lambda: self.experiment_double_clicked.emit(metadata)
        )
        
        menu.addSeparator()
        
        explore_action = menu.addAction("Show in Explorer")
        explore_action.triggered.connect(lambda: self._show_in_explorer(metadata))
        
        duplicate_action = menu.addAction("Duplicate Experiment")
        duplicate_action.triggered.connect(lambda: self._duplicate_experiment(metadata))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete Experiment")
        delete_action.setStyleSheet("color: #e74c3c;")  # Red text
        delete_action.triggered.connect(lambda: self._delete_experiment(metadata))
        
        menu.exec(self.tree.mapToGlobal(position))
    
    def _show_in_explorer(self, metadata: ExperimentMetadata):
        """Open experiment folder in file explorer."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(metadata.path)))
    
    def _duplicate_experiment(self, metadata: ExperimentMetadata):
        """Duplicate an experiment."""
        new_name, ok = QInputDialog.getText(
            self, "Duplicate Experiment",
            "Enter name for duplicated experiment:",
            text=f"{metadata.name}_copy"
        )
        
        if ok and new_name:
            if self.model.duplicate_experiment(metadata.name, new_name):
                self._refresh()
                QMessageBox.information(
                    self, "Success",
                    f"Experiment duplicated as {new_name}"
                )
            else:
                QMessageBox.warning(
                    self, "Error",
                    "Failed to duplicate experiment"
                )
    
    def _delete_experiment(self, metadata: ExperimentMetadata):
        """Delete an experiment with confirmation."""
        reply = QMessageBox.question(
            self, "Delete Experiment",
            f"Are you sure you want to delete {metadata.name}?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.model.delete_experiment(metadata.name):
                self.experiment_deleted.emit(metadata.name)
                QMessageBox.information(self, "Deleted", f"Experiment {metadata.name} deleted.")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete experiment.")
    
    def _show_error(self, error_message: str):
        """Show error dialog."""
        QMessageBox.critical(self, "Error", error_message)
    
    def _refresh(self):
        """Refresh the experiment list."""
        self.model.refresh()
