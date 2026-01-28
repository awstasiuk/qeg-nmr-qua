"""Script editor widget with syntax highlighting and line numbers."""

from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QColor, QPainter, QTextFormat, QFont, QPalette,
    QTextCursor
)

from gui.widgets.syntax_highlighter import PythonSyntaxHighlighter


class LineNumberArea(QWidget):
    """Widget for displaying line numbers alongside the editor."""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class ScriptEditor(QPlainTextEdit):
    """
    Code editor widget with syntax highlighting, line numbers, and NMR-specific features.
    """
    
    # Signals
    content_modified = pyqtSignal(bool)  # Emitted when content changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._is_modified = False
        self._current_file = None
        
        # Set up font
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.setFont(font)
        
        # Set tab width to 4 spaces
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(' '))
        
        # Enable line wrap
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Set up line number area
        self.line_number_area = LineNumberArea(self)
        
        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.textChanged.connect(self._on_text_changed)
        
        # Initial setup
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        
        # Set up syntax highlighter
        self.highlighter = PythonSyntaxHighlighter(self.document())
        
        # Set placeholder text
        self.setPlaceholderText(
            "# Python experiment script\n"
            "# Create a new experiment to generate template code\n"
            "# Or open an existing script file\n"
            "#\n"
            "# Example structure:\n"
            "# import qeg_nmr_qua as qnmr\n"
            "# settings = qnmr.ExperimentSettings(...)\n"
            "# cfg = qnmr.cfg_from_settings(settings)\n"
            "# expt = qnmr.Experiment1D(config=cfg, settings=settings)\n"
            "# expt.add_pulse(...)\n"
            "# expt.execute_experiment()\n"
        )
    
    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def update_line_number_area_width(self, _):
        """Update the viewport margins to accommodate line numbers."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
    
    def update_line_number_area(self, rect, dy):
        """Update the line number area when scrolling."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)
    
    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )
    
    def line_number_area_paint_event(self, event):
        """Paint the line numbers."""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(40, 40, 40))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        
        # Draw line numbers
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(150, 150, 150))
                painter.drawText(
                    0, top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number
                )
            
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1
    
    def highlight_current_line(self):
        """Highlight the line containing the cursor."""
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            
            line_color = QColor(60, 60, 60)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)
    
    def _on_text_changed(self):
        """Handle text changes."""
        if not self._is_modified:
            self._is_modified = True
            self.content_modified.emit(True)
    
    def set_content(self, text: str):
        """Set editor content and reset modified flag."""
        self.setPlainText(text)
        self._is_modified = False
        self.content_modified.emit(False)
    
    def get_content(self) -> str:
        """Get editor content."""
        return self.toPlainText()
    
    def is_modified(self) -> bool:
        """Check if content has been modified."""
        return self._is_modified
    
    def clear_modified(self):
        """Clear the modified flag."""
        self._is_modified = False
        self.content_modified.emit(False)
    
    def set_current_file(self, filepath: str):
        """Set the current file path."""
        self._current_file = filepath
    
    def get_current_file(self) -> str:
        """Get the current file path."""
        return self._current_file
    
    def insert_text_at_cursor(self, text: str):
        """Insert text at the current cursor position."""
        cursor = self.textCursor()
        cursor.insertText(text)
        self.setTextCursor(cursor)
