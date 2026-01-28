# QEG NMR QUA - GUI

Graphical User Interface for managing NMR experiments on the OPX-1000.

## Installation

To install the GUI dependencies, run:

```bash
pip install -e ".[gui]"
```

## Running the GUI

After installation, you can launch the GUI with:

```bash
qnmr-gui
```

Or directly with Python:

```bash
python -m gui.main
```

## Current Status: Phase 1 (Complete)

Phase 1 implements the core structure:

- ✅ Main window with dock panels
- ✅ Settings editor with validation
- ✅ Console widget for logging
- ✅ Menu bar and toolbar
- ✅ Dark theme stylesheet

## Features

### Settings Editor
- Organized parameter groups (Pulse, Timing, Frequency, etc.)
- Real-time validation with visual feedback
- Unit conversion helpers
- Load/Save settings from JSON files
- Restore defaults

### Console
- Color-coded messages (info, warning, error, success, debug)
- Auto-scrolling
- Clear console button

### Main Window
- Dockable, resizable panels
- File menu (New, Open, Save, Exit)
- Edit menu (Settings, Preferences)
- Run menu (Execute, Simulate, Stop)
- Help menu (Documentation, About)

## Coming Soon

### Phase 2: Experiment Management
- Experiment browser
- Load/save experiments
- File tree navigation
- Metadata preview

### Phase 3: Script Editor
- Python syntax highlighting
- Code editor with line numbers
- Template system
- Quick command builder

### Phase 4: Plotting
- Matplotlib integration
- Live plotting during execution
- Multi-plot support
- Analysis tools (FFT, fitting, etc.)

### Phase 5: Polish
- Custom theming
- User preferences
- Enhanced error handling
- Comprehensive documentation

## Development

The GUI is structured using Model-View-Controller (MVC) pattern:

```
gui/
├── main.py              # Entry point
├── models/              # Data models
│   └── settings_model.py
├── views/               # UI components
│   ├── main_window.py
│   └── settings_editor.py
├── controllers/         # Application logic
├── widgets/             # Custom widgets
│   ├── console_widget.py
│   └── parameter_widgets.py
└── resources/           # Stylesheets, icons
    └── styles.qss
```

## Requirements

- Python >= 3.9
- PyQt6 >= 6.6.0
- matplotlib >= 3.8.0
- numpy >= 1.24.0
- qeg-nmr-qua core package

## License

MIT License - See LICENSE file for details.
