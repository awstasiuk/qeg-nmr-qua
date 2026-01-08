"""
Data Saving Module.

This module provides utilities for saving experiment data from NMR experiments
using the OPX-1000, including automated handling of NumPy arrays, matplotlib
figures, and other scientific computing types via :class:`QuantumEncoder`.
"""

import json
import re
import warnings
from pathlib import Path
from typing import Any

from qeg_nmr_qua.analysis.encoder import QuantumEncoder


class DataSaver:
    """Manage saving and loading of NMR experiment data with metadata.

    Provides a structured approach to persisting experiment configurations, settings,
    commands, and results to disk. Each experiment is saved to a uniquely named folder
    containing JSON files and optionally PNG figures.

    **Folder Structure:**

    Each saved experiment creates a folder with::

        experiment_001/
        ├── config.json          # OPX configuration
        ├── settings.json        # Experiment settings
        ├── commands.json        # Command sequence executed
        ├── data.json            # Experimental results and metadata
        ├── figures.json         # (Optional) Mapping of figure keys to filenames
        └── figure_*.png         # (Optional) Saved matplotlib figures

    **Data Handling:**

    - JSON-serializable data (dicts, lists, numbers, strings) are saved directly
    - NumPy arrays/scalars are converted to native Python types
    - Matplotlib figures are automatically saved as PNG files (300 dpi)
    - Non-serializable objects are converted to descriptive strings with warnings
    - Path objects are converted to strings

    **Error Recovery:**

    If saving fails, the partially created experiment folder is automatically
    cleaned up, maintaining a consistent state.

    Attributes:
        root_data_folder (Path): The root directory where experiment data will be saved.

    Example:
        >>> saver = DataSaver("./experiment_data")
        >>> config = {"qop_ip": "192.168.1.100", ...}
        >>> settings = {"n_avg": 8, ...}
        >>> commands = [{"type": "pulse", ...}]
        >>> data = {"I_data": np.array([...]), "Q_data": np.array([...])}
        >>> folder = saver.save_experiment("exp_001", config, settings, commands, data)
        >>> loaded = saver.load_experiment("exp_001")
    """

    def __init__(self, root_data_folder: str | Path):
        """Initialize the DataSaver with a root data folder.

        Creates the root data folder if it doesn't exist. All experiments will be
        saved as subfolders within this directory.

        Args:
            root_data_folder (str | Path): The root directory for saving experiment data.
                Can be a string path or Path object. Will be created with parents=True
                if it doesn't exist.

        Example:
            >>> saver = DataSaver("./data")
            >>> saver.root_data_folder
            PosixPath('data')
        """
        self.root_data_folder = Path(root_data_folder)
        self.root_data_folder.mkdir(parents=True, exist_ok=True)

    def save_experiment(
        self,
        experiment_prefix: str,
        config: dict[str, Any],
        settings: dict[str, Any],
        commands: list[dict[str, Any]],
        data: dict[str, Any],
    ) -> Path:
        """Save experiment metadata and data to a structured directory.

        Creates a folder with an auto-incremented name based on ``experiment_prefix``
        (e.g., ``prefix_0001``, ``prefix_0002``) and atomically saves
        OPX configuration, experiment settings, command sequence, and experimental
        results. Handles special data types (numpy arrays, matplotlib figures) and
        non-serializable objects gracefully.

        **Saved Files:**

        - ``config.json``: OPX-1000 configuration dictionary
        - ``settings.json``: Experiment settings (frequencies, pulse params, etc.)
        - ``commands.json``: List of pulse commands executed
        - ``data.json``: Experimental results and metadata (numpy arrays converted to lists)
        - ``figures.json``: (Optional) Mapping of data keys to saved figure filenames
        - ``figure_*.png``: (Optional) Matplotlib figures extracted from data

        **Data Processing:**

        - NumPy arrays are converted to JSON-serializable lists
        - NumPy scalars are converted to native Python types
        - Matplotlib figures are automatically saved as PNG files with 300 dpi
        - Non-serializable objects are converted to descriptive strings with warnings
        - Failed keys are tracked in ``_failed_keys`` in the saved data

        Args:
            experiment_prefix (str): Prefix for the experiment folder name (e.g., "experiment").
                The actual folder created will be ``<experiment_prefix>_NNNN`` with a
                zero-padded 4-digit counter (starting at 0001). Must not contain path
                separators or be ".".
            config (dict[str, Any]): OPX configuration dictionary from
                :meth:`~OPXConfig.to_dict`.
            settings (dict[str, Any]): Experiment settings dictionary from
                :meth:`~ExperimentSettings.to_dict`.
            commands (list[dict[str, Any]]): List of command dictionaries defining
                the pulse sequence.
            data (dict[str, Any]): Experimental data dictionary. Can contain numpy arrays,
                matplotlib figures, and other Python objects. NumPy types and figures
                are handled automatically.

        Returns:
            Path: The path to the created experiment folder.

        Raises:
            ValueError: If experiment_prefix contains path separators or is invalid.
            RuntimeError: If saving fails (folder is cleaned up on failure).

        Example:
            >>> saver = DataSaver("./data")
            >>> folder = saver.save_experiment(
            ...     "exp",
            ...     config={"qop_ip": "192.168.1.100"},
            ...     settings={"n_avg": 8},
            ...     commands=[{"type": "pulse", "name": "pi_half"}],
            ...     data={"I": np.array([1, 2, 3]), "Q": np.array([4, 5, 6])}
            ... )
            >>> folder.name  # first call
            'exp_0001'
        """
        # Validate experiment prefix
        if not isinstance(experiment_prefix, str) or experiment_prefix == "":
            raise ValueError("experiment_prefix must be a non-empty string.")
        if "/" in experiment_prefix or "\\" in experiment_prefix or experiment_prefix == ".":
            raise ValueError(
                f"Invalid experiment prefix '{experiment_prefix}'. "
                "Must be a simple name without path separators."
            )

        # Determine next available experiment folder name for this prefix
        experiment_name = self._next_experiment_name(experiment_prefix)
        experiment_folder = self.root_data_folder / experiment_name

        experiment_folder.mkdir(parents=True, exist_ok=False)

        try:
            # Save config
            self._save_json(experiment_folder / "config.json", config)

            # Save settings
            self._save_json(experiment_folder / "settings.json", settings)

            # Save commands
            self._save_json(experiment_folder / "commands.json", commands)

            # Process and save data (extract figures, handle failures gracefully)
            cleaned_data, figure_map = self._process_data_payload(
                data, experiment_folder
            )

            # Save the cleaned data (without figures)
            self._save_json(experiment_folder / "data.json", cleaned_data)

            # Save a mapping of figure keys to their filenames
            if figure_map:
                self._save_json(experiment_folder / "figures.json", figure_map)

            return experiment_folder

        except Exception as e:
            # Clean up on failure
            import shutil

            shutil.rmtree(experiment_folder, ignore_errors=True)
            raise RuntimeError(
                f"Failed to save experiment '{experiment_name}': {e}"
            ) from e

    def _next_experiment_name(self, prefix: str, width: int = 4) -> str:
        """Compute the next available experiment folder name for a prefix.

        Scans the root_data_folder for folders matching ``{prefix}_NNNN`` and
        returns the next sequential name, starting at ``{prefix}_0001`` if none exist.

        Args:
            prefix: The experiment prefix.
            width: Zero-padding width for the counter (default: 4).

        Returns:
            str: Next experiment folder name like ``prefix_0001``.
        """
        pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{{width}}})$")
        max_idx = 0
        if self.root_data_folder.exists():
            for entry in self.root_data_folder.iterdir():
                if entry.is_dir():
                    m = pattern.match(entry.name)
                    if m:
                        try:
                            idx = int(m.group(1))
                            if idx > max_idx:
                                max_idx = idx
                        except ValueError:
                            continue
        next_idx = max_idx + 1
        return f"{prefix}_{next_idx:0{width}d}"

    def load_experiment(self, experiment_name: str) -> dict[str, Any]:
        """Load experiment metadata and data from a saved folder.

        Reconstructs the complete experiment state from JSON files. Returns all
        saved data including configuration, settings, commands, and results.

        Args:
            experiment_name (str): Name of the experiment folder to load.

        Returns:
            dict[str, Any]: Dictionary with keys:
                - ``config``: OPX configuration
                - ``settings``: Experiment settings
                - ``commands``: Command sequence
                - ``data``: Experimental results
                - ``figures``: (Optional) Mapping of figure keys to filenames

        Raises:
            FileNotFoundError: If the experiment folder or required files don't exist.

        Example:
            >>> saver = DataSaver("./data")
            >>> loaded = saver.load_experiment("exp_001")
            >>> config = loaded["config"]
            >>> data = loaded["data"]
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

        # Load figure mapping if it exists
        figures_file = experiment_folder / "figures.json"
        if figures_file.exists():
            result["figures"] = self._load_json(figures_file)

        return result

    @staticmethod
    def _save_json(filepath: Path, data: Any, indent: int = 2) -> None:
        """Save data to a JSON file with NumPy type handling.

        Writes data to JSON format using the custom :class:`QuantumEncoder`, which handles
        NumPy arrays, scalars, and Path objects automatically.

        Args:
            filepath (Path): Path where the JSON file will be saved.
            data (Any): Data to serialize. Can contain numpy arrays, Path objects, etc.
            indent (int): JSON indentation level for human readability (default: 2).

        Raises:
            TypeError: If data contains non-serializable types not handled by :class:`QuantumEncoder`.
            OSError: If the file cannot be written.
        """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, cls=QuantumEncoder)

    @staticmethod
    def _load_json(filepath: Path) -> Any:
        """Load data from a JSON file.

        Reads and deserializes JSON data from file. Returns standard Python types
        (no automatic reconstruction of NumPy arrays).

        Args:
            filepath (Path): Path to the JSON file to load.

        Returns:
            Any: Deserialized JSON data (dict, list, str, int, float, bool, or None).

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _process_data_payload(
        self, data: dict[str, Any], experiment_folder: Path
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Process the data payload to extract matplotlib figures and handle serialization.

        Inspects each field in the data dictionary:

        - Matplotlib figures: Saved as PNG files, replaced with reference strings
        - NumPy arrays/scalars: Converted to native Python types by encoder
        - JSON-serializable objects: Passed through as-is
        - Non-serializable objects: Converted to descriptive strings with warnings

        Args:
            data (dict[str, Any]): The data payload that may contain figures, numpy
                arrays, and other objects.
            experiment_folder (Path): Folder where figures will be saved.

        Returns:
            tuple[dict[str, Any], dict[str, str]]: Tuple of:
                - cleaned_data: Data dict with figures removed, numpy types converted,
                  and failed keys recorded in ``_failed_keys``
                - figure_map: Dict mapping original data keys to saved figure filenames
        """
        cleaned_data = {}
        figure_map = {}
        failed_keys = []

        for key, value in data.items():
            try:
                # Check if value is a matplotlib figure
                if self._is_matplotlib_figure(value):
                    # Save figure as PNG
                    figure_filename = f"figure_{key}.png"
                    figure_path = experiment_folder / figure_filename
                    self._save_figure(value, figure_path)
                    figure_map[key] = figure_filename
                    # Replace with a reference string in the data
                    cleaned_data[key] = f"<figure saved as {figure_filename}>"
                else:
                    # Try to serialize the value
                    try:
                        # Test if it's JSON serializable
                        json.dumps(value, cls=QuantumEncoder)
                        cleaned_data[key] = value
                    except (TypeError, ValueError) as e:
                        # If serialization fails, save as string representation
                        warnings.warn(
                            f"Could not serialize data['{key}'] as JSON: {e}. "
                            f"Saving as string representation instead.",
                            UserWarning,
                        )
                        cleaned_data[key] = (
                            f"<non-serializable: {type(value).__name__}>"
                        )
                        failed_keys.append(key)
            except Exception as e:
                # If anything goes wrong, log and continue
                warnings.warn(
                    f"Failed to process data['{key}']: {e}. Skipping this field.",
                    UserWarning,
                )
                failed_keys.append(key)
                continue

        if failed_keys:
            cleaned_data["_failed_keys"] = failed_keys

        return cleaned_data, figure_map

    @staticmethod
    def _is_matplotlib_figure(obj: Any) -> bool:
        """Check if an object is a matplotlib Figure instance.

        Safely checks if the object is a matplotlib Figure without raising an error
        if matplotlib is not installed. Returns False if matplotlib is unavailable.

        Args:
            obj: Object to check.

        Returns:
            bool: True if obj is a matplotlib.figure.Figure, False otherwise.
        """
        try:
            import matplotlib.figure

            return isinstance(obj, matplotlib.figure.Figure)
        except ImportError:
            return False

    @staticmethod
    def _save_figure(fig: Any, filepath: Path) -> None:
        """Save a matplotlib figure to a PNG file.

        Saves the figure with 300 dpi resolution and tight bounding box for
        publication-quality output. Warnings are issued if the save fails,
        but execution continues.

        Args:
            fig: Matplotlib Figure object to save.
            filepath (Path): Path where the PNG file will be saved.

        Note:
            If saving fails, a UserWarning is issued and execution continues.
        """
        try:
            fig.savefig(filepath, dpi=300, bbox_inches="tight")
        except Exception as e:
            warnings.warn(f"Failed to save figure to {filepath}: {e}", UserWarning)

    def list_experiments(self) -> list[str]:
        """List all saved experiments in the root data folder.

        Scans the root folder and returns a sorted list of all experiment folders
        that contain a valid ``data.json`` file.

        Returns:
            list[str]: List of experiment folder names sorted alphabetically.
                Returns an empty list if no experiments have been saved.

        Example:
            >>> saver = DataSaver("./data")
            >>> experiments = saver.list_experiments()
            >>> experiments
            ['exp_001', 'exp_002', 'exp_003']
        """
        if not self.root_data_folder.exists():
            return []

        experiments = [
            d.name
            for d in self.root_data_folder.iterdir()
            if d.is_dir() and (d / "data.json").exists()
        ]
        return sorted(experiments)
