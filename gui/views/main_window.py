"""Main application window for QEG NMR QUA GUI."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QVBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QLabel,
    QMessageBox, QFileDialog, QTextEdit, QDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from gui.views.settings_editor import SettingsEditor
from gui.views.experiment_browser import ExperimentBrowser
from gui.views.new_experiment_dialog import NewExperimentDialog
from gui.widgets.recent_experiments_widget import RecentExperimentsWidget
from gui.widgets.console_widget import ConsoleWidget
from gui.models.settings_model import SettingsModel


class MainWindow(QMainWindow):
    """
    Main application window with dock panels for experiment management.
    
    Layout:
    - Left: Experiment Browser & File Tree (future)
    - Center: Script Editor OR Plot Viewer (future)
    - Right: Settings Panel
    - Bottom: Console/Output Log
    """
    
    def __init__(self):
        super().__init__()
        
        self.settings_model = SettingsModel()
        
        self._setup_ui()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()
        self._create_dock_widgets()
        
        self.setWindowTitle("QEG NMR QUA - Experiment Manager")
        self.resize(1400, 900)
    
    def _setup_ui(self):
        """Set up the central widget and basic UI."""
        # Central widget - placeholder for now
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        
        placeholder = QTextEdit()
        placeholder.setReadOnly(True)
        placeholder.setPlaceholderText(
            "Script Editor / Plot Viewer will appear here\n\n"
            "Phase 1: Core Structure\n"
            "Phase 2: Experiment Management\n"
            "Phase 3: Script Editor\n"
            "Phase 4: Plotting\n"
            "Phase 5: Polish"
        )
        
        central_layout.addWidget(placeholder)
        self.setCentralWidget(central_widget)
    
    def _create_menus(self):
        """Create the menu bar and menus."""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        
        self.new_action = QAction("&New Experiment", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.setStatusTip("Create a new experiment")
        self.new_action.triggered.connect(self._new_experiment)
        file_menu.addAction(self.new_action)
        
        file_menu.addSeparator()
        
        self.save_action = QAction("&Save Experiment", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setStatusTip("Save current experiment")
        self.save_action.triggered.connect(self._save_experiment)
        file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction("Save &As...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.setStatusTip("Save experiment with new name")
        self.save_as_action.triggered.connect(self._save_experiment_as)
        file_menu.addAction(self.save_as_action)
        
        file_menu.addSeparator()
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.setStatusTip("Exit application")
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        
        self.settings_action = QAction("&Settings", self)
        self.settings_action.setStatusTip("Edit experiment settings")
        self.settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(self.settings_action)
        
        edit_menu.addSeparator()
        
        self.preferences_action = QAction("&Preferences...", self)
        self.preferences_action.setStatusTip("Application preferences")
        self.preferences_action.triggered.connect(self._show_preferences)
        edit_menu.addAction(self.preferences_action)
        
        # View Menu
        view_menu = menubar.addMenu("&View")
        
        # Will be populated with dock widget toggles
        self.view_menu = view_menu
        
        # Run Menu
        run_menu = menubar.addMenu("&Run")
        
        self.execute_action = QAction("&Execute Experiment", self)
        self.execute_action.setShortcut(QKeySequence("Ctrl+R"))
        self.execute_action.setStatusTip("Execute the current experiment on hardware")
        self.execute_action.triggered.connect(self._execute_experiment)
        run_menu.addAction(self.execute_action)
        
        self.simulate_action = QAction("&Simulate Experiment", self)
        self.simulate_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        self.simulate_action.setStatusTip("Simulate the experiment without hardware")
        self.simulate_action.triggered.connect(self._simulate_experiment)
        run_menu.addAction(self.simulate_action)
        
        run_menu.addSeparator()
        
        self.stop_action = QAction("&Stop", self)
        self.stop_action.setShortcut(QKeySequence("Ctrl+C"))
        self.stop_action.setStatusTip("Stop the running experiment")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self._stop_experiment)
        run_menu.addAction(self.stop_action)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        
        self.docs_action = QAction("&Documentation", self)
        self.docs_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.docs_action.setStatusTip("Open documentation")
        self.docs_action.triggered.connect(self._show_documentation)
        help_menu.addAction(self.docs_action)
        
        help_menu.addSeparator()
        
        self.about_action = QAction("&About", self)
        self.about_action.setStatusTip("About QEG NMR QUA")
        self.about_action.triggered.connect(self._show_about)
        help_menu.addAction(self.about_action)
    
    def _create_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        
        # Add main actions to toolbar
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.execute_action)
        toolbar.addAction(self.simulate_action)
        toolbar.addAction(self.stop_action)
        
        self.addToolBar(toolbar)
    
    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Add permanent widgets
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)
        
        self.connection_label = QLabel("Not Connected")
        status_bar.addPermanentWidget(self.connection_label)
    
    def _create_dock_widgets(self):
        """Create and configure dock widgets."""
        # Right Dock: Settings Editor
        self.settings_dock = QDockWidget("Settings", self)
        self.settings_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self.settings_editor = SettingsEditor(self.settings_model)
        self.settings_editor.settings_updated.connect(self._on_settings_updated)
        self.settings_dock.setWidget(self.settings_editor)
        
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.settings_dock)
        self.view_menu.addAction(self.settings_dock.toggleViewAction())
        
        # Bottom Dock: Console
        self.console_dock = QDockWidget("Console", self)
        self.console_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        
        self.console = ConsoleWidget()
        self.console_dock.setWidget(self.console)
        
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)
        self.view_menu.addAction(self.console_dock.toggleViewAction())
        
        # Left Dock: Recent Experiments + Browser
        self.browser_dock = QDockWidget("Experiment Browser", self)
        self.browser_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        # Get data directory from settings
        data_dir = self.settings_model.settings.save_dir or Path("data")
        
        # Create a container with recent experiments and browser
        browser_container = QWidget()
        browser_layout = QVBoxLayout(browser_container)
        browser_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add recent experiments widget
        self.recent_experiments = RecentExperimentsWidget()
        self.recent_experiments.experiment_selected.connect(self._on_recent_experiment_selected)
        browser_layout.addWidget(self.recent_experiments, stretch=1)
        
        # Add browser
        self.browser = ExperimentBrowser(data_dir)
        self.browser.experiment_selected.connect(self._on_experiment_selected)
        self.browser.experiment_double_clicked.connect(self._on_experiment_double_clicked)
        browser_layout.addWidget(self.browser, stretch=2)
        
        self.browser_dock.setWidget(browser_container)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.browser_dock)
        self.view_menu.addAction(self.browser_dock.toggleViewAction())
        
        # Update recent experiments list
        recent_exps = self.browser.model.get_recent_experiments(5)
        self.recent_experiments.update_recent_experiments(recent_exps)
        
        # Connect browser refresh to update recent experiments
        self.browser.model.experiments_updated.connect(self._update_recent_experiments_list)
        
        # Log welcome message
        self.console.log_info("QEG NMR QUA GUI initialized")
        self.console.log_info("Phase 1: Core Structure - Complete")
        self.console.log_info("Phase 2: Experiment Management - Complete")
    
    def _update_recent_experiments_list(self):
        """Update the recent experiments list when experiments change."""
        recent_exps = self.browser.model.get_recent_experiments(5)
        self.recent_experiments.update_recent_experiments(recent_exps)
    
    # Experiment browser handlers
    
    @pyqtSlot(object)
    def _on_experiment_selected(self, metadata):
        """Handle experiment selection from browser."""
        if metadata:
            self.console.log_info(f"Selected experiment: {metadata.name}")
    
    @pyqtSlot(object)
    def _on_recent_experiment_selected(self, metadata):
        """Handle experiment selection from recent experiments widget."""
        if metadata:
            self.console.log_info(f"Loading recent experiment: {metadata.name}")
            self._load_experiment_from_metadata(metadata)
        else:
            self.console.log_info("Experiment deselected")
    
    @pyqtSlot(object)
    def _on_experiment_double_clicked(self, metadata):
        """Handle double-click on experiment - load it."""
        if not metadata:
            return
        self._load_experiment_from_metadata(metadata)
    
    def _load_experiment_from_metadata(self, metadata):
        """Load experiment settings from metadata."""
        if not metadata:
            return
        
        self.console.log_info(f"Loading experiment: {metadata.name}")
        
        try:
            # Load experiment data using the browser model
            exp_data = self.browser.model.load_experiment(metadata.name)
            
            if not exp_data:
                self.console.log_error(f"Failed to load experiment data")
                return
            
            # Load settings into the settings editor
            if "settings" in exp_data:
                from qeg_nmr_qua.config.settings import ExperimentSettings
                settings = ExperimentSettings.from_dict(exp_data["settings"])
                self.settings_editor.set_settings(settings)
                self.console.log_success(f"Loaded settings from {metadata.name}")
            
            self.console.log_info(f"Experiment loaded: {metadata.name}")
            
        except Exception as e:
            self.console.log_error(f"Error loading experiment: {str(e)}")
    
    # Menu action handlers
    
    @pyqtSlot()
    def _new_experiment(self):
        """Create a new experiment."""
        dialog = NewExperimentDialog(self)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.console.log_info("New experiment cancelled")
            return
        
        if not dialog.is_valid():
            QMessageBox.warning(
                self, "Invalid Name",
                "Please enter a valid experiment name.\n"
                "Use only letters, numbers, underscores, and hyphens.\n"
                "Do not end with numbers (reserved for auto-numbering)."
            )
            return
        
        # Get values
        values = dialog.get_values()
        name_prefix = values["name"]
        exp_type = values["type"]
        
        # Get current settings
        settings = self.settings_editor.get_settings()
        config = self._get_current_config()
        
        try:
            # Create the experiment
            exp_name = self._create_and_save_experiment(
                name_prefix, exp_type, settings, config
            )
            
            self.console.log_success(f"Created experiment: {exp_name}")
            self.console.log_info(f"Type: {exp_type}, Averages: {settings.n_avg}")
            
            # Refresh browser to show new experiment
            self.browser.model.refresh()
            
            # Show the browser
            self.browser_dock.show()
            self.browser_dock.raise_()
            
        except Exception as e:
            self.console.log_error(f"Failed to create experiment: {str(e)}")
            QMessageBox.critical(
                self, "Error",
                f"Failed to create experiment:\n{str(e)}"
            )
    
    @pyqtSlot()
    def _save_experiment(self):
        """Save current experiment."""
        self.console.log_info("Save experiment - Coming in Phase 2")
        QMessageBox.information(
            self, "Save Experiment",
            "Save experiment functionality will be implemented in Phase 2."
        )
    
    @pyqtSlot()
    def _save_experiment_as(self):
        """Save experiment with new name."""
        self.console.log_info("Save As - Coming in Phase 2")
        QMessageBox.information(
            self, "Save As",
            "Save As functionality will be implemented in Phase 2."
        )
    
    @pyqtSlot()
    def _show_settings(self):
        """Show/focus settings dock."""
        self.settings_dock.show()
        self.settings_dock.raise_()
    
    @pyqtSlot()
    def _show_preferences(self):
        """Show application preferences dialog."""
        self.console.log_info("Preferences - Coming in Phase 5")
        QMessageBox.information(
            self, "Preferences",
            "Application preferences will be implemented in Phase 5."
        )
    
    @pyqtSlot()
    def _execute_experiment(self):
        """Execute the current experiment."""
        self.console.log_info("Execute experiment - Coming in Phase 3")
        QMessageBox.information(
            self, "Execute",
            "Experiment execution will be implemented in Phase 3."
        )
    
    @pyqtSlot()
    def _simulate_experiment(self):
        """Simulate the current experiment."""
        self.console.log_info("Simulate experiment - Coming in Phase 3")
        QMessageBox.information(
            self, "Simulate",
            "Experiment simulation will be implemented in Phase 3."
        )
    
    @pyqtSlot()
    def _stop_experiment(self):
        """Stop the running experiment."""
        self.console.log_warning("Stop requested")
    
    @pyqtSlot()
    def _show_documentation(self):
        """Open documentation in browser."""
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        
        # Open local docs if available, else online
        docs_path = Path(__file__).parent.parent.parent / "docs" / "_build" / "html" / "index.html"
        if docs_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(docs_path)))
            self.console.log_info(f"Opening documentation: {docs_path}")
        else:
            self.console.log_warning("Local documentation not found")
            QMessageBox.warning(
                self, "Documentation",
                "Documentation not found. Please build the docs using 'make html' in the docs directory."
            )
    
    @pyqtSlot()
    def _show_about(self):
        """Show about dialog."""
        about_text = """
        <h2>QEG NMR QUA</h2>
        <p>Graphical User Interface for NMR Experiments on OPX-1000</p>
        <p>Version: 0.1.0 (Alpha)</p>
        <p>A tool for managing quantum machine experiments with:</p>
        <ul>
            <li>Visual settings editor</li>
            <li>Script management</li>
            <li>Live data visualization</li>
            <li>Experiment history</li>
        </ul>
        """
        QMessageBox.about(self, "About QEG NMR QUA", about_text)
    
    @pyqtSlot()
    def _on_settings_updated(self):
        """Handle settings updates."""
        self.console.log_debug("Settings updated")
        self.status_label.setText("Settings modified")
    
    # Helper methods
    
    def _get_current_config(self):
        """Get the current OPX configuration."""
        try:
            from qeg_nmr_qua.config.config_from_settings import cfg_from_settings
            settings = self.settings_editor.get_settings()
            return cfg_from_settings(settings)
        except Exception as e:
            self.console.log_warning(f"Could not generate config: {e}")
            return None
    
    def _create_and_save_experiment(self, name_prefix: str, exp_type: str, settings, config) -> str:
        """
        Create a new experiment and save it to disk.
        
        Args:
            name_prefix: Experiment prefix (e.g., 'calibration')
            exp_type: Experiment type ('1D', '2D', 'Custom')
            settings: ExperimentSettings object
            config: OPXConfig object
            
        Returns:
            The created experiment folder name (e.g., 'calibration_0001')
        """
        from qeg_nmr_qua.analysis.data_saver import DataSaver
        
        # Get save directory
        save_dir = settings.save_dir or Path("data")
        
        # Create DataSaver and initialize with empty data
        saver = DataSaver(save_dir)
        
        # Convert config and settings to dicts for serialization
        config_dict = config.to_dict() if config else {}
        settings_dict = settings.to_dict() if hasattr(settings, 'to_dict') else {}
        commands = []  # Empty commands list for new experiment
        data = {
            "experiment_type": exp_type,
            "metadata": {
                "created_from": "GUI",
                "initial_n_avg": settings.n_avg,
            }
        }
        
        # Save the experiment - pass serialized dicts instead of objects
        experiment_path = saver.save_experiment(
            name_prefix,
            config_dict,  # Pass serialized config dict
            settings_dict,  # Pass serialized settings dict
            commands,
            data
        )
        
        # Extract the folder name from the path
        return experiment_path.name
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.settings_model.is_modified:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved settings changes. Do you want to exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        self.console.log_info("Application closing")
        event.accept()
