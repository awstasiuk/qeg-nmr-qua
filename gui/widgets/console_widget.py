"""Console widget for displaying log messages and status updates."""

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import pyqtSlot, Qt
from PyQt6.QtGui import QTextCursor, QColor


class ConsoleWidget(QTextEdit):
    """
    A read-only console widget for displaying colored log messages.
    
    Supports different message types with color coding:
    - INFO: Blue
    - WARNING: Orange
    - ERROR: Red
    - SUCCESS: Green
    - DEBUG: Gray
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Define color scheme
        self.colors = {
            "info": QColor("#5dade2"),      # Blue
            "warning": QColor("#f39c12"),   # Orange
            "error": QColor("#e74c3c"),     # Red
            "success": QColor("#2ecc71"),   # Green
            "debug": QColor("#95a5a6"),     # Gray
            "default": QColor("#e0e0e0"),   # Light gray
        }
    
    @pyqtSlot(str, str)
    def append_message(self, message: str, msg_type: str = "default"):
        """
        Append a message to the console with the appropriate color.
        
        Args:
            message: The message text to display
            msg_type: Type of message ('info', 'warning', 'error', 'success', 'debug', 'default')
        """
        color = self.colors.get(msg_type.lower(), self.colors["default"])
        
        # Move cursor to end
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        
        # Set text color and insert message
        self.setTextColor(color)
        self.insertPlainText(message + "\n")
        
        # Scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    @pyqtSlot()
    def clear_console(self):
        """Clear all text from the console."""
        self.clear()
    
    def log_info(self, message: str):
        """Log an informational message."""
        self.append_message(f"[INFO] {message}", "info")
    
    def log_warning(self, message: str):
        """Log a warning message."""
        self.append_message(f"[WARNING] {message}", "warning")
    
    def log_error(self, message: str):
        """Log an error message."""
        self.append_message(f"[ERROR] {message}", "error")
    
    def log_success(self, message: str):
        """Log a success message."""
        self.append_message(f"[SUCCESS] {message}", "success")
    
    def log_debug(self, message: str):
        """Log a debug message."""
        self.append_message(f"[DEBUG] {message}", "debug")
