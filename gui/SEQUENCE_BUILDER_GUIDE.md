# Sequence Builder Guide

## Overview

The Sequence Builder is the primary interface for creating NMR pulse sequences visually. It provides a drag-and-drop workflow for building experiments without writing code.

## Features

### Visual Sequence Construction
- **Tree View**: Hierarchical display of pulse sequence steps
- **Color Coding**: 
  - 🔵 Blue = Pulse steps
  - 🟠 Orange = Delay steps
  - 🟢 Green = Loop steps
- **Drag and Drop**: Reorder steps by moving them up/down

### Step Types

#### Pulse Step
Configure NMR pulses with:
- **Pulse Name**: pi_half, pi, pi_x, pi_y, etc. (or custom)
- **Element**: Target element (default: "resonator")
- **Amplitude**: -0.5 to 0.5 (or "Use Default")
- **Phase**: -360° to 360° (or "Default")
- **Sweep (2D)**: Enable amplitude sweeps for 2D experiments
  - Start/End values
  - Number of points

#### Delay Step
Configure timing delays with:
- **Duration**: Numeric value
- **Units**: nanoseconds / microseconds / milliseconds
- **Auto-conversion**: Shows equivalent durations in other units

#### Loop Step
Repeat a sequence of steps:
- **Iterations**: Number of times to repeat
- **Nested Steps**: Add pulse/delay steps inside the loop

### Operations

#### Adding Steps
- Click **➕ Pulse**, **⏱ Delay**, or **🔁 Loop** buttons
- Configure parameters in dialog
- Step appears in tree view

#### Editing Steps
- **Double-click** any step to edit
- **Right-click** for context menu → Edit

#### Reordering Steps
- Select step, click **↑ Move Up** or **↓ Move Down**
- Right-click → Move Up / Move Down

#### Deleting Steps
- Select step, click **❌ Delete**
- Right-click → Delete
- **🗑 Clear All** removes entire sequence

### Code Generation

The sequence builder automatically generates Python code:

1. **Auto-Sync**: Every change updates the Script Editor (Advanced) tab
2. **Manual Sync**: Click **🔄 Sync Code** button in toolbar
3. **View Code**: Switch to "Script Editor (Advanced)" tab

Generated code structure:
```python
# Import statements
import qeg_nmr_qua as qnmr
from qualang_tools.units import unit
import numpy as np

# Load active settings
settings = qnmr.ExperimentSettings.from_json("active-settings.json")

# Generate config
cfg = qnmr.cfg_from_settings(settings)

# Create experiment (1D or 2D based on sweeps)
expt = qnmr.Experiment1D(config=cfg, settings=settings)

# Build pulse sequence
expt.add_pulse(name="pi_half", element="resonator")
expt.add_delay(100 * u.us)
```

### Experiment Types

#### 1D Experiment
- No amplitude sweeps
- Simple pulse sequences
- Example: Spin echo, FID

#### 2D Experiment
- At least one pulse with amplitude sweep enabled
- Creates 2D data arrays
- Example: Rabi oscillation, T1/T2 mapping

Type is **auto-detected** based on sweep parameters.

## Workflow

### Creating a New Experiment

1. **File → New Experiment**
2. Choose experiment type (1D or 2D)
3. Sequence Builder opens with basic template:
   - 1D: Single pi_half pulse
   - 2D: pi_half pulse with amplitude sweep enabled
4. Add/edit/reorder steps as needed
5. Code auto-generates in script editor

### Loading Settings

Settings automatically load from `active-settings.json`:
- **Auto-Save**: Settings editor saves on every change
- **Active Settings**: Scripts always reference current settings
- **No Hardcoding**: Parameters come from settings file

### Executing Experiments

1. Build sequence in Sequence Builder
2. Verify generated code in Script Editor (Advanced) tab
3. Click **▶ Run** in toolbar (Phase 4 - coming soon)
4. View results in Plot Viewer tab

## Tips

### Best Practices
- Start with simple sequences and build up
- Use descriptive pulse names
- Group repeated operations in loops
- Check generated code to understand what's happening

### Common Patterns

**Spin Echo**:
```
1. Pulse (pi_half)
2. Delay (tau)
3. Pulse (pi)
4. Delay (tau)
```

**CPMG**:
```
1. Pulse (pi_half)
2. Loop (n iterations)
   - Delay (tau)
   - Pulse (pi)
   - Delay (tau)
```

**Rabi Oscillation** (2D):
```
1. Pulse (pi, amplitude sweep: 0.0 → 1.0, 50 points)
```

### Troubleshooting

**Code not updating?**
- Click 🔄 Sync Code button
- Check console for errors

**Can't add steps?**
- Make sure sequence builder is selected
- Try clicking directly in tree area

**Wrong experiment type?**
- Add/remove amplitude sweeps as needed
- Type auto-updates based on sweeps

## Advanced: Script Editor

For users comfortable with Python:
1. Switch to "Script Editor (Advanced)" tab
2. View or manually edit generated code
3. Add custom logic not available in visual builder
4. Save as .py file for reuse

**Note**: Manual script edits are not synced back to sequence builder.

## Phase 3 Status: Complete ✅

- ✅ Sequence step models (Pulse, Delay, Loop)
- ✅ Visual tree widget with color coding
- ✅ Add/Edit/Delete/Reorder operations
- ✅ Configuration dialogs (Pulse, Delay)
- ✅ Code generation from sequence
- ✅ Auto-sync to script editor
- ✅ Main window integration
- ⏳ Loop editing (basic support)
- ⏳ Execute/Simulate buttons (Phase 4)
