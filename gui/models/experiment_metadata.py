"""Data structures for experiment metadata and management."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class ExperimentMetadata:
    """
    Metadata for a saved experiment.
    
    Provides a structured view of experiment information without loading
    all data into memory.
    """
    
    name: str                          # Experiment folder name (e.g., "exp_0001")
    path: Path                         # Full path to experiment folder
    date: datetime                     # Creation date
    n_avg: int                         # Number of averages
    experiment_type: str               # Type (e.g., "1D", "2D", "Custom")
    settings_summary: Dict[str, Any]   # Subset of key settings
    command_count: int                 # Number of commands executed
    has_data: bool = False             # Whether data.json exists
    has_figures: bool = False          # Whether figures were saved
    
    @property
    def display_name(self) -> str:
        """Get a human-readable name with date."""
        return f"{self.name} ({self.date.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def info_dict(self) -> Dict[str, str]:
        """Get formatted info for display."""
        return {
            "Name": self.name,
            "Date": self.date.strftime('%Y-%m-%d %H:%M:%S'),
            "Type": self.experiment_type,
            "Averages": str(self.n_avg),
            "Commands": str(self.command_count),
            "Data": "Yes" if self.has_data else "No",
            "Figures": "Yes" if self.has_figures else "No",
        }
