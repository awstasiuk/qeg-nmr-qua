"""
Live Plotting Module.

This module provides real-time plotting utilities for NMR experiments
using the OPX-1000.
"""

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure


class LivePlotter:
    """
    Real-time plotting utility for NMR experiments.

    This class provides methods for creating and updating live plots
    during NMR data acquisition.

    Attributes:
        fig: Matplotlib figure object.
        axes: Dictionary of axes objects.
        lines: Dictionary of line objects for updating.
        title: Title of the plot.
    """

    def __init__(
        self,
        title: str = "NMR Live Data",
        figsize: tuple[int, int] = (10, 6),
        style: str = "seaborn-v0_8-whitegrid",
    ) -> None:
        """
        Initialize the LivePlotter.

        Args:
            title: Title for the plot window.
            figsize: Figure size as (width, height) in inches.
            style: Matplotlib style to use.
        """
        self.title = title
        self.figsize = figsize
        self.fig: Figure | None = None
        self.axes: dict[str, Any] = {}
        self.lines: dict[str, Any] = {}
        self._style = style

        # Enable interactive mode
        plt.ion()

    def create_subplot(
        self,
        name: str,
        position: int | tuple[int, int, int] = 111,
        xlabel: str = "Time",
        ylabel: str = "Signal",
        title: str | None = None,
    ) -> None:
        """
        Create a subplot for live plotting.

        Args:
            name: Unique identifier for this subplot.
            position: Subplot position (e.g., 111, 211, 212).
            xlabel: Label for x-axis.
            ylabel: Label for y-axis.
            title: Optional title for the subplot.
        """
        if self.fig is None:
            try:
                plt.style.use(self._style)
            except OSError:
                pass  # Style not available, use default
            self.fig = plt.figure(figsize=self.figsize)
            self.fig.suptitle(self.title)

        ax = self.fig.add_subplot(position)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        if title:
            ax.set_title(title)
        ax.grid(True, alpha=0.3)

        self.axes[name] = ax

    def add_line(
        self,
        subplot_name: str,
        line_name: str,
        color: str = "blue",
        linestyle: str = "-",
        marker: str = "",
        label: str | None = None,
    ) -> None:
        """
        Add a line to a subplot for data visualization.

        Args:
            subplot_name: Name of the subplot to add line to.
            line_name: Unique identifier for this line.
            color: Line color.
            linestyle: Line style (-, --, :, etc.).
            marker: Data point marker.
            label: Legend label for the line.
        """
        if subplot_name not in self.axes:
            raise ValueError(f"Subplot '{subplot_name}' does not exist. Create it first.")

        ax = self.axes[subplot_name]
        (line,) = ax.plot(
            [],
            [],
            color=color,
            linestyle=linestyle,
            marker=marker,
            label=label,
        )
        self.lines[line_name] = line

        if label:
            ax.legend(loc="best")

    def update_line(
        self,
        line_name: str,
        x_data: np.ndarray,
        y_data: np.ndarray,
        autoscale: bool = True,
    ) -> None:
        """
        Update a line with new data.

        Args:
            line_name: Name of the line to update.
            x_data: New x-axis data.
            y_data: New y-axis data.
            autoscale: Whether to autoscale axes to fit data.
        """
        if line_name not in self.lines:
            raise ValueError(f"Line '{line_name}' does not exist. Add it first.")

        line = self.lines[line_name]
        line.set_xdata(x_data)
        line.set_ydata(y_data)

        if autoscale:
            ax = line.axes
            ax.relim()
            ax.autoscale_view()

        self._refresh()

    def append_point(
        self,
        line_name: str,
        x: float,
        y: float,
        max_points: int | None = None,
    ) -> None:
        """
        Append a single point to a line.

        Args:
            line_name: Name of the line to update.
            x: New x value.
            y: New y value.
            max_points: Maximum number of points to keep (for rolling display).
        """
        if line_name not in self.lines:
            raise ValueError(f"Line '{line_name}' does not exist. Add it first.")

        line = self.lines[line_name]
        x_data = np.append(line.get_xdata(), x)
        y_data = np.append(line.get_ydata(), y)

        if max_points and len(x_data) > max_points:
            x_data = x_data[-max_points:]
            y_data = y_data[-max_points:]

        line.set_xdata(x_data)
        line.set_ydata(y_data)

        ax = line.axes
        ax.relim()
        ax.autoscale_view()

        self._refresh()

    def clear_line(self, line_name: str) -> None:
        """
        Clear all data from a line.

        Args:
            line_name: Name of the line to clear.
        """
        if line_name not in self.lines:
            raise ValueError(f"Line '{line_name}' does not exist.")

        line = self.lines[line_name]
        line.set_xdata([])
        line.set_ydata([])
        self._refresh()

    def _refresh(self) -> None:
        """Refresh the plot display."""
        if self.fig is not None:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()

    def show(self) -> None:
        """Display the plot and block."""
        plt.ioff()
        plt.show()

    def close(self) -> None:
        """Close the plot window and cleanup."""
        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None
            self.axes.clear()
            self.lines.clear()

    def save_figure(self, filepath: str, dpi: int = 150) -> None:
        """
        Save the current figure to a file.

        Args:
            filepath: Path to save the figure.
            dpi: Resolution in dots per inch.
        """
        if self.fig is not None:
            self.fig.savefig(filepath, dpi=dpi, bbox_inches="tight")
