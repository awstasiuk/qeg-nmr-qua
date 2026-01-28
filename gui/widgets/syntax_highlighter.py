"""Python syntax highlighter for script editor."""

import re
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for Python code with NMR-specific keywords.
    """
    
    def __init__(self, document):
        super().__init__(document)
        
        # Define color scheme (dark theme compatible)
        self.formats = {}
        
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))  # Blue
        keyword_format.setFontWeight(QFont.Weight.Bold)
        self.formats['keyword'] = keyword_format
        
        # Built-in functions
        builtin_format = QTextCharFormat()
        builtin_format.setForeground(QColor("#4EC9B0"))  # Cyan
        self.formats['builtin'] = builtin_format
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))  # Orange
        self.formats['string'] = string_format
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))  # Green
        comment_format.setFontItalic(True)
        self.formats['comment'] = comment_format
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))  # Light green
        self.formats['number'] = number_format
        
        # NMR-specific commands
        nmr_format = QTextCharFormat()
        nmr_format.setForeground(QColor("#DCDCAA"))  # Yellow
        nmr_format.setFontWeight(QFont.Weight.Bold)
        self.formats['nmr'] = nmr_format
        
        # Define highlighting rules
        self.rules = []
        
        # Python keywords
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]
        self.rules.append((
            QRegularExpression(r'\b(' + '|'.join(keywords) + r')\b'),
            self.formats['keyword']
        ))
        
        # Built-in functions
        builtins = [
            'abs', 'all', 'any', 'bin', 'bool', 'chr', 'dict', 'dir',
            'enumerate', 'filter', 'float', 'format', 'hex', 'int', 'len',
            'list', 'map', 'max', 'min', 'oct', 'ord', 'pow', 'print',
            'range', 'repr', 'round', 'set', 'sorted', 'str', 'sum',
            'tuple', 'type', 'zip'
        ]
        self.rules.append((
            QRegularExpression(r'\b(' + '|'.join(builtins) + r')\b'),
            self.formats['builtin']
        ))
        
        # NMR-specific commands
        nmr_commands = [
            'pulse', 'wait', 'measure', 'align', 'reset_phase',
            'frame_rotation', 'save', 'loop', 'for_', 'assign',
            'play', 'set_frequency', 'update_frequency'
        ]
        self.rules.append((
            QRegularExpression(r'\b(' + '|'.join(nmr_commands) + r')\b'),
            self.formats['nmr']
        ))
        
        # Numbers (integers and floats)
        self.rules.append((
            QRegularExpression(r'\b[+-]?[0-9]+\.?[0-9]*([eE][+-]?[0-9]+)?\b'),
            self.formats['number']
        ))
        
        # Double-quoted strings
        self.rules.append((
            QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'),
            self.formats['string']
        ))
        
        # Single-quoted strings
        self.rules.append((
            QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"),
            self.formats['string']
        ))
        
        # Comments
        self.rules.append((
            QRegularExpression(r'#[^\n]*'),
            self.formats['comment']
        ))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to a block of text."""
        # Apply all rules
        for pattern, format_style in self.rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_style)
