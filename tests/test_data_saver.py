"""
Unit tests for the DataSaver class.
"""

import json
import tempfile
from pathlib import Path
import pytest
import numpy as np

from qeg_nmr_qua.analysis.data_saver import DataSaver


class TestDataSaver:
    """Test suite for the DataSaver class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_init_creates_directory(self, temp_dir):
        """Test that DataSaver creates the root data folder if it doesn't exist."""
        data_dir = temp_dir / "new_data_dir"
        assert not data_dir.exists()

        saver = DataSaver(data_dir)
        assert data_dir.exists()
        assert saver.root_data_folder == data_dir

    def test_save_experiment_creates_folder_structure(self, temp_dir):
        """Test that save_experiment creates the proper folder structure."""
        saver = DataSaver(temp_dir)

        config = {"test": "config"}
        settings = {"test": "settings"}
        commands = [{"type": "pulse"}]
        data = {"results": [1, 2, 3]}

        result_path = saver.save_experiment(
            experiment_name="test_exp_001",
            config=config,
            settings=settings,
            commands=commands,
            data=data,
        )

        # Check folder was created
        assert result_path.exists()
        assert result_path.name == "test_exp_001"

        # Check all required files exist
        assert (result_path / "config.json").exists()
        assert (result_path / "settings.json").exists()
        assert (result_path / "commands.json").exists()
        assert (result_path / "data.json").exists()

    def test_save_experiment_saves_correct_data(self, temp_dir):
        """Test that save_experiment saves the correct data to files."""
        saver = DataSaver(temp_dir)

        config = {"qop_ip": "192.168.88.253"}
        settings = {"n_avg": 4, "pulse_length": 1100}
        commands = [{"type": "pulse", "name": "pi_half", "element": "resonator"}]
        data = {"results": np.array([1.0, 2.0, 3.0])}

        result_path = saver.save_experiment(
            experiment_name="test_exp_002",
            config=config,
            settings=settings,
            commands=commands,
            data=data,
        )

        # Load and verify files
        with open(result_path / "config.json") as f:
            loaded_config = json.load(f)
        assert loaded_config == config

        with open(result_path / "settings.json") as f:
            loaded_settings = json.load(f)
        assert loaded_settings == settings

        with open(result_path / "commands.json") as f:
            loaded_commands = json.load(f)
        assert loaded_commands == commands

        with open(result_path / "data.json") as f:
            loaded_data = json.load(f)
        assert loaded_data["results"] == [1.0, 2.0, 3.0]  # numpy array converted

    def test_save_experiment_rejects_invalid_names(self, temp_dir):
        """Test that save_experiment rejects invalid experiment names."""
        saver = DataSaver(temp_dir)

        invalid_names = [
            "exp/with/slashes",
            "exp\\with\\backslashes",
            ".",
        ]

        for invalid_name in invalid_names:
            with pytest.raises(ValueError):
                saver.save_experiment(
                    experiment_name=invalid_name,
                    config={},
                    settings={},
                    commands=[],
                    data={},
                )

    def test_save_experiment_prevents_overwrite(self, temp_dir):
        """Test that save_experiment prevents overwriting existing experiments."""
        saver = DataSaver(temp_dir)

        # Create first experiment
        saver.save_experiment(
            experiment_name="existing_exp",
            config={},
            settings={},
            commands=[],
            data={},
        )

        # Try to create with same name
        with pytest.raises(FileExistsError):
            saver.save_experiment(
                experiment_name="existing_exp",
                config={},
                settings={},
                commands=[],
                data={},
            )

    def test_load_experiment(self, temp_dir):
        """Test loading a saved experiment."""
        saver = DataSaver(temp_dir)

        # Save experiment
        config = {"qop_ip": "192.168.88.253"}
        settings = {"n_avg": 4}
        commands = [{"type": "pulse"}]
        data = {"results": [1, 2, 3]}

        saver.save_experiment(
            experiment_name="test_load",
            config=config,
            settings=settings,
            commands=commands,
            data=data,
        )

        # Load experiment
        loaded = saver.load_experiment("test_load")

        assert loaded["config"] == config
        assert loaded["settings"] == settings
        assert loaded["commands"] == commands
        assert loaded["data"] == data

    def test_load_nonexistent_experiment(self, temp_dir):
        """Test that loading a nonexistent experiment raises FileNotFoundError."""
        saver = DataSaver(temp_dir)

        with pytest.raises(FileNotFoundError):
            saver.load_experiment("nonexistent")

    def test_list_experiments(self, temp_dir):
        """Test listing saved experiments."""
        saver = DataSaver(temp_dir)

        # Initially empty
        assert saver.list_experiments() == []

        # Add some experiments
        for i in range(3):
            saver.save_experiment(
                experiment_name=f"experiment_{i:03d}",
                config={},
                settings={},
                commands=[],
                data={},
            )

        experiments = saver.list_experiments()
        assert len(experiments) == 3
        assert experiments == ["experiment_000", "experiment_001", "experiment_002"]

    def test_numpy_array_serialization(self, temp_dir):
        """Test that numpy arrays are properly serialized."""
        saver = DataSaver(temp_dir)

        numpy_data = {
            "array": np.array([1.5, 2.5, 3.5]),
            "scalar_float": np.float64(3.14),
            "scalar_int": np.int32(42),
            "scalar_bool": np.bool_(True),
            "path": Path("/some/data/path"),
        }

        saver.save_experiment(
            experiment_name="numpy_test",
            config={},
            settings={},
            commands=[],
            data=numpy_data,
        )

        loaded = saver.load_experiment("numpy_test")

        # Check conversions
        assert loaded["data"]["array"] == [1.5, 2.5, 3.5]
        assert isinstance(loaded["data"]["scalar_float"], float)
        assert isinstance(loaded["data"]["scalar_int"], int)
        assert isinstance(loaded["data"]["scalar_bool"], bool)
        # Path should be serialized as a string (platform-independent comparison)
        assert isinstance(loaded["data"]["path"], str)
        assert "some" in loaded["data"]["path"] and "data" in loaded["data"]["path"]

    def test_matplotlib_figure_handling(self, temp_dir):
        """Test that matplotlib figures are saved as PNG files."""
        pytest.importorskip("matplotlib")
        import matplotlib.pyplot as plt

        saver = DataSaver(temp_dir)

        # Create a simple figure
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_title("Test Plot")

        data_with_figure = {
            "result": [1, 2, 3],
            "my_plot": fig,
            "description": "test experiment",
        }

        saver.save_experiment(
            experiment_name="figure_test",
            config={},
            settings={},
            commands=[],
            data=data_with_figure,
        )

        plt.close(fig)

        # Check that figure was saved
        figure_path = temp_dir / "figure_test" / "figure_my_plot.png"
        assert figure_path.exists()

        # Check that data.json has reference instead of figure
        loaded = saver.load_experiment("figure_test")
        assert "my_plot" in loaded["data"]
        assert "figure saved as" in loaded["data"]["my_plot"]
        assert loaded["data"]["result"] == [1, 2, 3]
        assert loaded["data"]["description"] == "test experiment"

    def test_non_serializable_data_handling(self, temp_dir):
        """Test that non-serializable data is handled gracefully."""
        saver = DataSaver(temp_dir)

        # Create data with a non-serializable object
        class CustomClass:
            def __init__(self, value):
                self.value = value

        data_with_nonserialization = {
            "good_data": [1, 2, 3],
            "bad_data": CustomClass(42),
            "more_good_data": "test",
        }

        # This should not raise an exception
        with pytest.warns(UserWarning, match="Could not serialize"):
            saver.save_experiment(
                experiment_name="mixed_test",
                config={},
                settings={},
                commands=[],
                data=data_with_nonserialization,
            )

        # Check that good data was saved
        loaded = saver.load_experiment("mixed_test")
        assert loaded["data"]["good_data"] == [1, 2, 3]
        assert loaded["data"]["more_good_data"] == "test"
        assert "non-serializable" in loaded["data"]["bad_data"]
        assert "_failed_keys" in loaded["data"]
        assert "bad_data" in loaded["data"]["_failed_keys"]

    def test_partial_save_resilience(self, temp_dir):
        """Test that partial failures don't prevent other data from being saved."""
        saver = DataSaver(temp_dir)

        # Mix of good and problematic data
        mixed_data = {
            "array": np.array([1, 2, 3]),
            "string": "hello",
            "number": 42,
            "lambda_func": lambda x: x + 1,  # Non-serializable
        }

        with pytest.warns(UserWarning):
            result_path = saver.save_experiment(
                experiment_name="partial_test",
                config={},
                settings={},
                commands=[],
                data=mixed_data,
            )

        assert result_path.exists()

        # Verify the good data was saved
        loaded = saver.load_experiment("partial_test")
        assert loaded["data"]["array"] == [1, 2, 3]
        assert loaded["data"]["string"] == "hello"
        assert loaded["data"]["number"] == 42
