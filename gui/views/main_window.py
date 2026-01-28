"""Main application window for QEG NMR QUA GUI."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QWidget, QVBoxLayout,
    QMenuBar, QMenu, QToolBar, QStatusBar, QLabel,
    QMessageBox, QFileDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from gui.views.settings_editor import SettingsEditor
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
        
        self.open_action = QAction("&Open Experiment...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setStatusTip("Open an existing experiment")
        self.open_action.triggered.connect(self._open_experiment)
        file_menu.addAction(self.open_action)
        
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
        toolbar.addAction(self.open_action)
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
        
        # Left Dock: Experiment Browser (placeholder for Phase 2)
        self.browser_dock = QDockWidget("Experiment Browser", self)
        self.browser_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        browser_placeholder = QLabel("Experiment Browser\n(Coming in Phase 2)")
        browser_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        browser_placeholder.setStyleSheet("color: #888888; font-style: italic;")
        self.browser_dock.setWidget(browser_placeholder)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.browser_dock)
        self.view_menu.addAction(self.browser_dock.toggleViewAction())
        
        # Log welcome message
        self.console.log_info("QEG NMR QUA GUI initialized")
        self.console.log_info("Phase 1: Core Structure - Complete")
    
    # Menu action handlers
    
    @pyqtSlot()
    def _new_experiment(self):
        """Create a new experiment."""
        self.console.log_info("New experiment - Coming in Phase 2")
        QMessageBox.information(
            self, "New Experiment",
            "New experiment functionality will be implemented in Phase 2."
        )
    
    @pyqtSlot()
    def _open_experiment(self):
        """Open an existing experiment."""
        self.console.log_info("Open experiment - Coming in Phase 2")
        QMessageBox.information(
            self, "Open Experiment",
            "Open experiment functionality will be implemented in Phase 2."
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
