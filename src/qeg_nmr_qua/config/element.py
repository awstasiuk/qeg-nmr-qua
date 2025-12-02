"""
OPX-1000 Element Configuration Module.

This module provides configuration utilities for the OPX-1000 LF-FEM
for solid state NMR experiments.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class digitalElementConfig:
    """Configuration for a digital element's paired input/output."""

    port: tuple[
        str, int, int
    ]  # (controller_name, chasis_slot, port_number) for digital trigger
    delay: int = 0  # in nanoseconds?
    buffer: int = 0  # in nanoseconds?

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "delay": self.delay,
            "buffer": self.buffer,
        }

    def to_opx_config(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass
class Element:
    """
    Configuration for an Element. An element's inputs are the OPX's outputs and vice
    versa. An element represents a physical connection to the OPX-1000, like the NMR probe,
    refered to a as a `resonator`.
    """

    name: str
    frequency: float  # in Hz
    # from OPX (controller_name, chasis_slot, port_number)
    analog_input: tuple[str, int, int]
    # to OPX (controller_name, chasis_slot, port_number)
    analog_output: tuple[str, int, int]
    # operation name with digitalElementConfig
    digital_inputs: dict[str, digitalElementConfig] = field(default_factory=dict)
    # operation name to pulse-config name mapping
    operations: dict[str, str] = field(default_factory=dict)
    # in nanoseconds, delay between output and input signals
    time_of_flight: float = 0.0
    # whether the element retains state between operations
    sticky: bool = False

    def add_digital_input(
        self,
        operation: str,
        controller_name: str,
        chasis_slot: int,
        port_number: int,
        delay: int = 0,
        buffer: int = 0,
    ) -> None:
        """
        Add a digital input configuration for a specific operation.

        Args:
            operation: Name of the digital operation (e.g "marker").
            controller_name: Name of the OPX controller.
            chasis_slot: Physical slot number in chassis.
            port_number: Digital port number on the OPX.
            delay: Delay in nanoseconds.
            buffer: Buffer time in nanoseconds.
        """

        self.digital_inputs[operation] = digitalElementConfig(
            port=(controller_name, chasis_slot, port_number),
            delay=delay,
            buffer=buffer,
        )

    def to_opx_config(self) -> dict[str, Any]:
        """Convert the Element configuration to a dictionary."""
        dct = {
            "singleInput": {"port": self.analog_input},
            "intermediate_frequency": self.frequency,
            "outputs": {"out1": self.analog_output},
            "digitalInputs": {
                name: input.to_opx_config()
                for name, input in self.digital_inputs.items()
            },
            "operations": self.operations,
            "time_of_flight": self.time_of_flight,
        }
        if self.sticky:
            dct["sticky"] = {"analog": self.sticky, "digital": self.sticky}
        return dct

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "frequency": self.frequency,
            "analog_input": self.analog_input,
            "analog_output": self.analog_output,
            "digital_inputs": {
                name: input.to_dict() for name, input in self.digital_inputs.items()
            },
            "operations": self.operations,
            "time_of_flight": self.time_of_flight,
            "sticky": self.sticky,
        }


@dataclass
class ElementConfig:
    """
    Container for multiple Element configurations.
    """

    elements: dict[str, Element] = field(default_factory=dict)

    def add_element(
        self,
        name: str,
        element: Element,
    ) -> None:
        """
        Add an element configuration.

        Args:
            name: Name of the element.
            frequency: Operating frequency in Hz.
            analog_input: Tuple specifying the analog input (controller_name, chasis_slot, port_number).
            analog_output: Tuple specifying the analog output (controller_name, chasis_slot, port_number).
            time_of_flight: Delay between output and input signals in nanoseconds.
            sticky: Whether the element retains state between operations.
        """
        self.elements[name] = element

    def to_dict(self) -> dict[str, Any]:
        """Convert the Element configurations to a dictionary."""
        return {name: element.to_dict() for name, element in self.elements.items()}

    def to_opx_config(self) -> dict[str, Any]:
        """Convert the Element configurations to OPX configuration format."""
        return {
            name: element.to_opx_config() for name, element in self.elements.items()
        }
