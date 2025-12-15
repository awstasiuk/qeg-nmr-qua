"""
Data Saving Module.

This module provides utilities for saving experiment data
from NMR experiments using the OPX-1000.
"""

import json
from pathlib import Path
from typing import Any
import numpy as np


class DataSaver:
    """
    A class to handle saving experiment data and metadata to a structured directory.

    Each experiment is saved to a uniquely named folder within the specified data directory.
    The folder structure preserves all metadata (config, settings, commands) and experimental data.

    Attributes:
        root_data_folder (Path): The root directory where experiment data will be saved.
    """

    def __init__(self, root_data_folder: str | Path):
        """
        Initialize the DataSaver with a root data folder.

        Args:
            root_data_folder (str | Path): The root directory for saving experiment data.
                Will be created if it doesn't exist.
        """
        self.root_data_folder = Path(root_data_folder)
        self.root_data_folder.mkdir(parents=True, exist_ok=True)

    def save_experiment(
        self,
        experiment_name: str,
        config: dict[str, Any],
        settings: dict[str, Any],
        commands: list[dict[str, Any]],
        data: dict[str, Any],
    ) -> Path:
        """
        Save experiment metadata and data to a structured directory.

        Creates a folder with the specified experiment_name and saves:
        - config.json: OPX configuration
        - settings.json: Experiment settings
        - commands.json: List of commands executed
        - data.json: Experimental results and metadata

        Args:
            experiment_name (str): Name for the experiment folder (e.g., "experiment_001").
                Must be a simple, non-nested name.
            config (dict): OPX configuration dictionary
            settings (dict): Experiment settings dictionary
            commands (list): List of command dictionaries
            data (dict): Experimental data dictionary (can include metadata and results)

        Returns:
            Path: The path to the created experiment folder

        Raises:
            ValueError: If experiment_name contains path separators or is invalid
            FileExistsError: If the experiment folder already exists
        """
        # Validate experiment name
        if "/" in experiment_name or "\\" in experiment_name or experiment_name == ".":
            raise ValueError(
                f"Invalid experiment name '{experiment_name}'. "
                "Must be a simple name without path separators."
            )

        # Create experiment folder
        experiment_folder = self.root_data_folder / experiment_name

        if experiment_folder.exists():
            raise FileExistsError(
                f"Experiment folder already exists at {experiment_folder}"
            )

        experiment_folder.mkdir(parents=True, exist_ok=False)

        try:
            # Save config
            self._save_json(experiment_folder / "config.json", config)

            # Save settings
            self._save_json(experiment_folder / "settings.json", settings)

            # Save commands
            self._save_json(experiment_folder / "commands.json", commands)

            # Save data
            self._save_json(experiment_folder / "data.json", data)

            return experiment_folder

        except Exception as e:
            # Clean up on failure
            import shutil

            shutil.rmtree(experiment_folder, ignore_errors=True)
            raise RuntimeError(
                f"Failed to save experiment '{experiment_name}': {e}"
            ) from e

    def load_experiment(self, experiment_name: str) -> dict[str, Any]:
        """
        Load experiment metadata and data from a saved folder.

        Args:
            experiment_name (str): Name of the experiment folder to load

        Returns:
            dict: Dictionary containing 'config', 'settings', 'commands', and 'data' keys

        Raises:
            FileNotFoundError: If the experiment folder or required files don't exist
        """
        experiment_folder = self.root_data_folder / experiment_name

        if not experiment_folder.exists():
            raise FileNotFoundError(
                f"Experiment folder not found at {experiment_folder}"
            )

        result = {}

        # Load each file
        required_files = ["config.json", "settings.json", "commands.json", "data.json"]
        for filename in required_files:
            filepath = experiment_folder / filename
            if not filepath.exists():
                raise FileNotFoundError(
                    f"Required file '{filename}' not found in {experiment_folder}"
                )
            key = filename.replace(".json", "")
            result[key] = self._load_json(filepath)

        return result

    @staticmethod
    def _save_json(filepath: Path, data: Any, indent: int = 2) -> None:
        """
        Save data to a JSON file with custom handling for numpy types.

        Args:
            filepath (Path): Path to save the JSON file
            data (Any): Data to serialize
            indent (int): JSON indentation level
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, cls=_NumpyEncoder)

    @staticmethod
    def _load_json(filepath: Path) -> Any:
        """
        Load data from a JSON file.

        Args:
            filepath (Path): Path to the JSON file

        Returns:
            Any: Deserialized JSON data
        """
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_experiments(self) -> list[str]:
        """
        List all experiment folders in the root data folder.

        Returns:
            list[str]: List of experiment folder names, sorted alphabetically
        """
        if not self.root_data_folder.exists():
            return []

        experiments = [
            d.name
            for d in self.root_data_folder.iterdir()
            if d.is_dir() and (d / "data.json").exists()
        ]
        return sorted(experiments)


class _NumpyEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle numpy types.

    Converts:
    - numpy arrays to lists
    - numpy scalars to Python native types
    """

    def default(self, obj):
        """Encode numpy types as JSON-serializable Python types."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)
