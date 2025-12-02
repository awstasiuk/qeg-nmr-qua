"""Tests for the qeg_nmr_qua package (updated for the refactor).

These tests exercise the new `OPXConfig` API and the DataSaver/LivePlotter
behaviour. They are intentionally small and focus on surface behaviour rather
than exhaustive validation of every helper class.
"""

import json
import tempfile
from pathlib import Path

import matplotlib

# Set non-interactive backend early to avoid GUI issues when LivePlotter imports matplotlib
matplotlib.use("Agg")

import numpy as np
import pytest

from qeg_nmr_qua import DataSaver, LivePlotter, OPXConfig, __version__

"""Tests for the qeg_nmr_qua package (updated for the refactor).

These tests exercise the new `OPXConfig` API and the DataSaver/LivePlotter
behaviour. They are intentionally small and focus on surface behaviour rather
than exhaustive validation of every helper class.
"""

import json
import tempfile
from pathlib import Path

import matplotlib

# Set non-interactive backend early to avoid GUI issues when LivePlotter imports matplotlib
matplotlib.use("Agg")

import numpy as np
import pytest

from qeg_nmr_qua import DataSaver, LivePlotter, OPXConfig, __version__
from qeg_nmr_qua.config.element import Element


class TestOPXConfig:
    def test_defaults_and_containers(self) -> None:
        opx = OPXConfig()
        assert opx.qop_ip == "192.168.88.253"
        assert opx.cluster == "lex"
        assert hasattr(opx, "controllers")
        assert hasattr(opx, "elements")
        assert hasattr(opx, "pulses")
        assert hasattr(opx, "waveforms")

    def test_add_element_pulse_waveform_and_integration(self) -> None:
        opx = OPXConfig()

        elm = Element(
            name="probe",
            frequency=376.5e6,
            analog_input=("con1", 1, 1),
            analog_output=("con1", 1, 1),
        )
        opx.add_element("probe", elm)

        # use pulse helpers
        opx.pulses.add_control_pulse("pi", length=1000, waveform="pi_wf")

        # add waveforms and integration weights
        opx.add_waveform("pi_wf", 0.5)
        opx.add_digital_waveform("marker1", state=1, length=100)
        opx.add_integration_weight("w1", length=1000, real_weight=1.0, imag_weight=0.0)

        cfg = opx.to_opx_config()

        assert "probe" in cfg["elements"]
        assert "pi" in cfg["pulses"]
        assert "pi_wf" in cfg["waveforms"]
        assert "marker1" in cfg["digital_waveforms"]
        assert "w1" in cfg["integration_weights"]


class TestDataSaver:
    def test_init_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "test_data"
            saver = DataSaver(base_path=data_path)
            assert data_path.exists()
            assert saver.experiment_name == "nmr_experiment"

    def test_save_and_load_hdf5_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            saver = DataSaver(base_path=tmpdir)

            original_data = {
                "x": np.array([1.0, 2.0, 3.0]),
                "y": np.array([4.0, 5.0, 6.0]),
            }
            original_metadata = {"test_key": "test_value"}

            filepath = saver.save_hdf5(
                original_data, original_metadata, filename="test_file"
            )

            loaded_data, loaded_metadata = saver.load_hdf5(filepath)

            np.testing.assert_array_equal(loaded_data["x"], original_data["x"])
            np.testing.assert_array_equal(loaded_data["y"], original_data["y"])
            assert loaded_metadata["test_key"] == "test_value"

    def test_save_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            saver = DataSaver(base_path=tmpdir)
            config_data = {"param1": 100, "param2": "test", "param3": [1, 2, 3]}
            filepath = saver.save_json(config_data, filename="test_config")
            assert filepath.exists()
            with open(filepath) as f:
                loaded = json.load(f)
            assert loaded == config_data


class TestLivePlotter:
    def test_basic_plot_lifecycle(self) -> None:
        plotter = LivePlotter(title="Test Plot", figsize=(6, 4))
        plotter.create_subplot("main")
        plotter.add_line("main", "data")

        x = np.linspace(0, 2 * np.pi, 50)
        y = np.sin(x)
        plotter.update_line("data", x, y)

        line = plotter.lines["data"]
        np.testing.assert_array_equal(line.get_xdata(), x)
        np.testing.assert_array_equal(line.get_ydata(), y)

        # save figure
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "fig.png"
            plotter.save_figure(str(filepath))
            assert filepath.exists()

        plotter.close()


class TestPackageImport:
    def test_version(self) -> None:
        assert __version__ == "0.1.0"

    def test_exports_present(self) -> None:
        import qeg_nmr_qua as qnmr

        assert hasattr(qnmr, "OPXConfig")
        assert hasattr(qnmr, "DataSaver")
        assert hasattr(qnmr, "LivePlotter")


class TestDataSaver:
    """Tests for DataSaver class."""

    def test_init_creates_directory(self) -> None:
        """Test that initialization creates the data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_path = Path(tmpdir) / "test_data"
            saver = DataSaver(base_path=data_path)
            assert data_path.exists()
            assert saver.experiment_name == "nmr_experiment"

    def test_save_hdf5(self) -> None:
        """Test saving data to HDF5 format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saver = DataSaver(base_path=tmpdir, experiment_name="test_exp")

            data = {
                "time": np.linspace(0, 1, 100),
                "signal": np.sin(np.linspace(0, 2 * np.pi, 100)),
            }
            metadata = {"sample_rate": 1000, "experiment_type": "FID"}

            filepath = saver.save_hdf5(data, metadata)

            assert filepath.exists()
            assert filepath.suffix == ".h5"

    def test_save_and_load_hdf5(self) -> None:
        """Test saving and loading HDF5 data round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saver = DataSaver(base_path=tmpdir)

            original_data = {
                "x": np.array([1.0, 2.0, 3.0]),
                "y": np.array([4.0, 5.0, 6.0]),
            }
            original_metadata = {"test_key": "test_value"}

            filepath = saver.save_hdf5(
                original_data, original_metadata, filename="test_file"
            )

            loaded_data, loaded_metadata = saver.load_hdf5(filepath)

            np.testing.assert_array_equal(loaded_data["x"], original_data["x"])
            np.testing.assert_array_equal(loaded_data["y"], original_data["y"])
            assert loaded_metadata["test_key"] == "test_value"

    def test_save_json(self) -> None:
        """Test saving configuration to JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            saver = DataSaver(base_path=tmpdir)

            config_data = {"param1": 100, "param2": "test", "param3": [1, 2, 3]}

            filepath = saver.save_json(config_data, filename="test_config")

            assert filepath.exists()
            assert filepath.suffix == ".json"

            with open(filepath) as f:
                loaded = json.load(f)

            assert loaded == config_data


class TestLivePlotter:
    """Tests for LivePlotter class."""

    def test_init(self) -> None:
        """Test LivePlotter initialization."""
        plotter = LivePlotter(title="Test Plot", figsize=(8, 5))
        assert plotter.title == "Test Plot"
        assert plotter.figsize == (8, 5)
        plotter.close()

    def test_create_subplot(self) -> None:
        """Test creating a subplot."""
        plotter = LivePlotter()
        plotter.create_subplot(
            name="main",
            xlabel="Time (s)",
            ylabel="Signal (V)",
            title="Signal vs Time",
        )

        assert "main" in plotter.axes
        assert plotter.fig is not None
        plotter.close()

    def test_add_and_update_line(self) -> None:
        """Test adding and updating a line."""
        plotter = LivePlotter()
        plotter.create_subplot("main")
        plotter.add_line("main", "signal", color="red", label="Signal")

        assert "signal" in plotter.lines

        x_data = np.linspace(0, 1, 50)
        y_data = np.sin(2 * np.pi * x_data)
        plotter.update_line("signal", x_data, y_data)

        line = plotter.lines["signal"]
        np.testing.assert_array_equal(line.get_xdata(), x_data)
        np.testing.assert_array_equal(line.get_ydata(), y_data)

        plotter.close()

    def test_append_point(self) -> None:
        """Test appending points to a line."""
        plotter = LivePlotter()
        plotter.create_subplot("main")
        plotter.add_line("main", "data")

        plotter.append_point("data", 0.0, 1.0)
        plotter.append_point("data", 1.0, 2.0)
        plotter.append_point("data", 2.0, 3.0)

        line = plotter.lines["data"]
        np.testing.assert_array_equal(line.get_xdata(), [0.0, 1.0, 2.0])
        np.testing.assert_array_equal(line.get_ydata(), [1.0, 2.0, 3.0])

        plotter.close()

    def test_clear_line(self) -> None:
        """Test clearing a line."""
        plotter = LivePlotter()
        plotter.create_subplot("main")
        plotter.add_line("main", "data")

        plotter.update_line("data", np.array([1, 2, 3]), np.array([4, 5, 6]))
        plotter.clear_line("data")

        line = plotter.lines["data"]
        assert len(line.get_xdata()) == 0
        assert len(line.get_ydata()) == 0

        plotter.close()

    def test_save_figure(self) -> None:
        """Test saving figure to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plotter = LivePlotter()
            plotter.create_subplot("main")
            plotter.add_line("main", "data")

            x = np.linspace(0, 2 * np.pi, 100)
            plotter.update_line("data", x, np.sin(x))

            filepath = Path(tmpdir) / "test_figure.png"
            plotter.save_figure(str(filepath))

            assert filepath.exists()
            plotter.close()

    def test_error_on_missing_subplot(self) -> None:
        """Test error when adding line to non-existent subplot."""
        plotter = LivePlotter()

        with pytest.raises(ValueError, match="does not exist"):
            plotter.add_line("nonexistent", "line")

        plotter.close()

    def test_error_on_missing_line(self) -> None:
        """Test error when updating non-existent line."""
        plotter = LivePlotter()
        plotter.create_subplot("main")

        with pytest.raises(ValueError, match="does not exist"):
            plotter.update_line("nonexistent", np.array([1]), np.array([1]))

        plotter.close()


class TestPackageImport:
    """Tests for package imports."""

    def test_version(self) -> None:
        """Test version is accessible."""
        from qeg_nmr_qua import __version__

        assert __version__ == "0.1.0"

    def test_all_exports(self) -> None:
        """Test all expected exports are available."""
        import qeg_nmr_qua

        assert hasattr(qeg_nmr_qua, "OPXConfig")
        assert hasattr(qeg_nmr_qua, "DataSaver")
        assert hasattr(qeg_nmr_qua, "LivePlotter")
