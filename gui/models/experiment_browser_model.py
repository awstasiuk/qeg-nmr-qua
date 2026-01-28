"""Model for managing experiment browser data."""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal

from gui.models.experiment_metadata import ExperimentMetadata


class ExperimentBrowserModel(QObject):
    """
    Qt model for managing experiment data from the file system.
    
    Provides signals for UI updates and methods for experiment operations.
    """
    
    # Signals
    experiments_updated = pyqtSignal()      # Emitted when experiment list changes
    experiment_loaded = pyqtSignal(dict)    # Emitted with experiment data
    error_occurred = pyqtSignal(str)        # Emitted on errors
    
    def __init__(self, root_data_folder: Path, parent=None):
        super().__init__(parent)
        self.root_folder = Path(root_data_folder)
        self.experiments: List[ExperimentMetadata] = []
        self._load_experiments()
    
    def _load_experiments(self):
        """Scan and load experiment metadata from the file system."""
        self.experiments.clear()
        
        if not self.root_folder.exists():
            return
        
        # Pattern for experiment folders: prefix_NNNN
        pattern = re.compile(r"^(.+)_(\d{4})$")
        
        for entry in sorted(self.root_folder.iterdir(), reverse=True):
            if not entry.is_dir():
                continue
            
            match = pattern.match(entry.name)
            if not match:
                continue
            
            try:
                metadata = self._load_metadata_from_folder(entry)
                if metadata:
                    self.experiments.append(metadata)
            except Exception as e:
                print(f"Warning: Could not load metadata for {entry.name}: {e}")
        
        self.experiments_updated.emit()
    
    def _load_metadata_from_folder(self, folder: Path) -> Optional[ExperimentMetadata]:
        """Load metadata from an experiment folder."""
        # Check for required files
        data_file = folder / "data.json"
        settings_file = folder / "settings.json"
        commands_file = folder / "commands.json"
        figures_file = folder / "figures.json"
        
        if not (data_file.exists() and settings_file.exists()):
            return None
        
        try:
            # Load settings for metadata
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            
            # Load commands count
            with open(commands_file, 'r') as f:
                commands = json.load(f)
            
            # Get file modification time as date
            date = datetime.fromtimestamp(data_file.stat().st_mtime)
            
            # Determine experiment type from data file
            with open(data_file, 'r') as f:
                data = json.load(f)
            
            exp_type = self._infer_experiment_type(data, commands)
            
            # Extract key settings for summary
            settings_summary = {
                "n_avg": settings.get("n_avg", 0),
                "center_freq": settings.get("center_freq", 0),
                "pulse_length": settings.get("pulse_length", 0),
            }
            
            metadata = ExperimentMetadata(
                name=folder.name,
                path=folder,
                date=date,
                n_avg=settings.get("n_avg", 0),
                experiment_type=exp_type,
                settings_summary=settings_summary,
                command_count=len(commands) if isinstance(commands, list) else 0,
                has_data=True,
                has_figures=figures_file.exists(),
            )
            
            return metadata
            
        except Exception as e:
            print(f"Error loading metadata from {folder}: {e}")
            return None
    
    def _infer_experiment_type(self, data: Dict[str, Any], commands: Any) -> str:
        """Infer experiment type from data and commands."""
        # Check for sweep axis (2D experiment)
        if "sweep_axis" in data or "sweep_label" in data:
            return "2D"
        
        # Check for loop structure in commands
        if isinstance(commands, list):
            for cmd in commands:
                if isinstance(cmd, dict) and cmd.get("type") == "loop":
                    return "2D"
        
        return "1D"
    
    def get_experiments(self) -> List[ExperimentMetadata]:
        """Get list of all experiments."""
        return self.experiments.copy()
    
    def get_recent(self, count: int = 10) -> List[ExperimentMetadata]:
        """Get the N most recent experiments."""
        return self.experiments[:count]
    
    def load_experiment(self, experiment_name: str) -> Optional[Dict[str, Any]]:
        """
        Load complete experiment data from disk.
        
        Returns:
            Dictionary with keys: config, settings, commands, data, figures (optional)
        """
        try:
            folder = self.root_folder / experiment_name
            
            if not folder.exists():
                self.error_occurred.emit(f"Experiment folder not found: {experiment_name}")
                return None
            
            result = {}
            
            # Load required files
            for filename in ["config.json", "settings.json", "commands.json", "data.json"]:
                filepath = folder / filename
                if filepath.exists():
                    with open(filepath, 'r') as f:
                        key = filename.replace(".json", "")
                        result[key] = json.load(f)
            
            # Load optional figures mapping
            figures_file = folder / "figures.json"
            if figures_file.exists():
                with open(figures_file, 'r') as f:
                    result["figures"] = json.load(f)
            
            self.experiment_loaded.emit(result)
            return result
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to load experiment: {str(e)}")
            return None
    
    def delete_experiment(self, experiment_name: str) -> bool:
        """
        Delete an experiment folder.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            folder = self.root_folder / experiment_name
            
            if not folder.exists():
                self.error_occurred.emit(f"Experiment folder not found: {experiment_name}")
                return False
            
            # Remove folder and all contents
            import shutil
            shutil.rmtree(folder)
            
            # Refresh experiment list
            self._load_experiments()
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to delete experiment: {str(e)}")
            return False
    
    def duplicate_experiment(self, experiment_name: str, new_name: str) -> bool:
        """
        Duplicate an experiment to a new folder.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            src_folder = self.root_folder / experiment_name
            dst_folder = self.root_folder / new_name
            
            if not src_folder.exists():
                self.error_occurred.emit(f"Source experiment not found: {experiment_name}")
                return False
            
            if dst_folder.exists():
                self.error_occurred.emit(f"Destination folder already exists: {new_name}")
                return False
            
            # Copy entire folder
            import shutil
            shutil.copytree(src_folder, dst_folder)
            
            # Refresh experiment list
            self._load_experiments()
            return True
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to duplicate experiment: {str(e)}")
            return False
    
    def refresh(self):
        """Refresh the experiment list from disk."""
        self._load_experiments()
    
    def get_recent_experiments(self, count: int = 5) -> List[ExperimentMetadata]:
        """
        Get the most recent experiments.
        
        Args:
            count: Number of recent experiments to return
            
        Returns:
            List of recent ExperimentMetadata objects, sorted by date (newest first)
        """
        # Already sorted newest first from _load_experiments
        return self.experiments[:count]
