# qeg-nmr-qua

NMR Control using the OPX-1000 LF-FEM for solid state nuclear magnetic resonance,
particularly for fluorine (19F) spins.

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Features

- **OPX-1000 Configuration**: Structured configuration management for the OPX-1000 low-frequency front-end module
- **Live Plotting**: Real-time data visualization during experiments
- **Data Saving**: HDF5 and JSON data export with metadata support

## Quick Start

### Configuration

```python
from qeg_nmr_qua import OPXConfig

# Create configuration for your OPX-1000
config = OPXConfig(
    host="192.168.1.100",
    fluorine_frequency=376.5e6  # 19F at 9.4T
)

# Add channels and pulses
config.add_channel("rf_out", port=1, offset=0.0)
config.add_pulse("pi_pulse", length=1000, amplitude=0.5)

# Get QUA-compatible configuration
qua_config = config.to_qua_config()
```

### Live Plotting

```python
from qeg_nmr_qua import LivePlotter
import numpy as np

# Create a live plotter
plotter = LivePlotter(title="NMR Signal")
plotter.create_subplot("fid", xlabel="Time (μs)", ylabel="Signal (V)")
plotter.add_line("fid", "signal", color="blue", label="FID")

# Update with data during acquisition
for i in range(100):
    # ... acquire data from OPX ...
    plotter.append_point("signal", time, value)

plotter.save_figure("fid_plot.png")
plotter.close()
```

### Data Saving

```python
from qeg_nmr_qua import DataSaver
import numpy as np

# Create data saver
saver = DataSaver(base_path="experiments/", experiment_name="fluorine_fid")

# Save experiment data
data = {
    "time": np.linspace(0, 1e-3, 1000),
    "signal": acquired_signal,
}
metadata = {
    "sample": "CaF2",
    "temperature": 300,
    "field_strength": 9.4,
}

filepath = saver.save_hdf5(data, metadata)
print(f"Data saved to: {filepath}")

# Load data later
loaded_data, loaded_metadata = saver.load_hdf5(filepath)
```

## Requirements

- Python >= 3.9
- qm-qua >= 1.1.0
- numpy >= 1.20.0
- matplotlib >= 3.5.0
- h5py >= 3.0.0

## License

MIT License - see [LICENSE](LICENSE) for details.
