"""
Data Saving Module.

This module provides utilities for saving experiment data
from NMR experiments using the OPX-1000.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import h5py
import numpy as np


class DataSaver:
    """
    Data saving utility for NMR experiments.

    This class provides methods for saving experiment data in HDF5 format
    with metadata and optional JSON configuration export.

    Attributes:
        base_path: Base directory for saving data files.
        experiment_name: Name of the current experiment.
    """

    def __init__(
        self,
        base_path: str | Path = "data",
        experiment_name: str = "nmr_experiment",
    ) -> None:
        """
        Initialize the DataSaver.

        Args:
            base_path: Base directory for saving data files.
            experiment_name: Name of the current experiment.
        """
        self.base_path = Path(base_path)
        self.experiment_name = experiment_name
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the base data directory exists."""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, suffix: str = "") -> Path:
        """
        Generate a unique filename based on timestamp.

        Args:
            suffix: Optional suffix to append to the filename.

        Returns:
            Path object for the generated filename.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{self.experiment_name}_{timestamp}"
        if suffix:
            name = f"{name}_{suffix}"
        return self.base_path / name

    def save_hdf5(
        self,
        data: dict[str, np.ndarray],
        metadata: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> Path:
        """
        Save experiment data to HDF5 format.

        Args:
            data: Dictionary mapping dataset names to numpy arrays.
            metadata: Optional dictionary of metadata to store.
            filename: Optional custom filename (without extension).

        Returns:
            Path to the saved file.
        """
        if filename:
            filepath = self.base_path / f"{filename}.h5"
        else:
            filepath = self._generate_filename().with_suffix(".h5")

        with h5py.File(filepath, "w") as f:
            # Save datasets
            for name, array in data.items():
                f.create_dataset(name, data=array, compression="gzip")

            # Save metadata as attributes
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        f.attrs[key] = value
                    elif isinstance(value, (list, tuple)):
                        f.attrs[key] = np.array(value)
                    else:
                        # Convert complex objects to JSON string
                        f.attrs[key] = json.dumps(value)

            # Add standard metadata
            f.attrs["experiment_name"] = self.experiment_name
            f.attrs["timestamp"] = datetime.now().isoformat()

        return filepath

    def save_json(
        self,
        data: dict[str, Any],
        filename: str | None = None,
    ) -> Path:
        """
        Save configuration or metadata to JSON format.

        Args:
            data: Dictionary of data to save.
            filename: Optional custom filename (without extension).

        Returns:
            Path to the saved file.
        """
        if filename:
            filepath = self.base_path / f"{filename}.json"
        else:
            filepath = self._generate_filename(suffix="config").with_suffix(".json")

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return filepath

    def load_hdf5(self, filepath: str | Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
        """
        Load experiment data from HDF5 format.

        Args:
            filepath: Path to the HDF5 file.

        Returns:
            Tuple of (data dictionary, metadata dictionary).
        """
        filepath = Path(filepath)
        data: dict[str, np.ndarray] = {}
        metadata: dict[str, Any] = {}

        with h5py.File(filepath, "r") as f:
            # Load datasets
            for name in f.keys():
                data[name] = np.array(f[name])

            # Load metadata from attributes
            for key, value in f.attrs.items():
                if isinstance(value, bytes):
                    metadata[key] = value.decode("utf-8")
                else:
                    metadata[key] = value

        return data, metadata
