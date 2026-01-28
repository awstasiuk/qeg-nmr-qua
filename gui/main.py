"""
Main entry point for the QEG NMR QUA GUI application.

Usage:
    python -m gui.main
    
Or after installation:
    qnmr-gui
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from gui.views.main_window import MainWindow


def load_stylesheet(app: QApplication):
    """Load the application stylesheet."""
    style_path = Path(__file__).parent / "resources" / "styles.qss"
    
    if style_path.exists():
        with open(style_path, 'r') as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: Stylesheet not found at {style_path}")


def main():
    """Main application entry point."""
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("QEG NMR QUA")
    app.setOrganizationName("QEG")
    app.setApplicationVersion("0.1.0")
    
    # Load stylesheet
    load_stylesheet(app)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
