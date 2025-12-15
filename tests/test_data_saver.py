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
