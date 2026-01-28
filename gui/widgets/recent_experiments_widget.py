"""Widget for displaying and accessing recent experiments."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from gui.models.experiment_metadata import ExperimentMetadata


class RecentExperimentsWidget(QWidget):
    """
    Widget displaying recent experiments with quick-load buttons.
    """
    
    # Signals
    experiment_selected = pyqtSignal(ExperimentMetadata)
    load_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.recent_experiments = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("Recent Experiments")
        font = header.font()
        font.setPointSize(font.pointSize() + 1)
        font.setBold(True)
        header.setFont(font)
        main_layout.addWidget(header)
        
        # List of recent experiments
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        main_layout.addWidget(self.list_widget)
        
        # Load button layout
        button_layout = QHBoxLayout()
        
        self.load_button = QPushButton("Load Most Recent Settings")
        self.load_button.clicked.connect(self._on_load_clicked)
        self.load_button.setEnabled(False)
        button_layout.addWidget(self.load_button)
        
        main_layout.addLayout(button_layout)
    
    def update_recent_experiments(self, experiments):
        """Update the list of recent experiments."""
        self.recent_experiments = experiments
        self.list_widget.clear()
        
        for exp in experiments:
            item = QListWidgetItem(exp.display_name)
            item.setData(Qt.ItemDataRole.UserRole, exp)
            self.list_widget.addItem(item)
        
        # Enable load button if there are experiments
        self.load_button.setEnabled(len(experiments) > 0)
    
    def _on_item_double_clicked(self, item):
        """Handle double-click on item."""
        metadata = item.data(Qt.ItemDataRole.UserRole)
        if metadata:
            self.experiment_selected.emit(metadata)
    
    def _on_load_clicked(self):
        """Handle load button click - loads most recent experiment."""
        if self.recent_experiments:
            # Load the first (most recent) experiment
            self.experiment_selected.emit(self.recent_experiments[0])
    
    def get_most_recent_experiment(self):
        """Get the most recent experiment metadata."""
        if self.recent_experiments:
            return self.recent_experiments[0]
        return None
