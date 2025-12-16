"""
OPX-1000 Element Configuration Module.

This module provides configuration utilities for the OPX-1000 LF-FEM
for solid state NMR experiments.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class digitalElementConfig:
    """Configuration for a digital element's paired input/output connection.

    Specifies how a digital marker or trigger signal is routed between the OPX
    and a physical element (like an RF switch or frequency marker).

    Attributes:
        port (tuple[str, int, int]): Physical port specification as
            (controller_name, chassis_slot, port_number). Example: ("con1", 1, 1)
            specifies controller 1, chassis slot 1, digital port 1.
        delay (int): Delay applied to the digital signal in nanoseconds (default: 0).
            Useful for synchronization with analog signals.
        buffer (int): Buffer/timing margin in nanoseconds (default: 0).
            Provides timing headroom for signal stabilization.
    """

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

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "digitalElementConfig":
        return cls(
            port=tuple(d.get("port", ("con1", 1, 1))),
            delay=d.get("delay", 0),
            buffer=d.get("buffer", 0),
        )

    def __repr__(self) -> str:
        return (
            f"<digitalElement port={self.port} delay={self.delay} buffer={self.buffer}>"
        )


@dataclass
class Element:
    """Configuration for a physical quantum element connected to the OPX-1000.

    An Element represents a physical connection to the OPX, such as a resonator,
    amplifier, or signal source. It aggregates analog I/O ports, digital control
    lines, and associated pulse operations.

    **Port Mapping:**

    In OPX convention:

    - ``analog_input``: The OPX's output port that drives this element
    - ``analog_output``: The OPX's input port that reads from this element
    - This naming convention reflects the signal direction relative to the element,
      not the OPX.

    Attributes:
        name (str): Unique identifier for this element (e.g., "resonator", "amplifier").
        frequency (float): Intermediate frequency (IF) of this element in Hz.
            For direct sampling, this is the actual RF frequency.
        analog_input (tuple[str, int, int]): Port specification for OPX output
            as (controller_name, chassis_slot, port_number).
        analog_output (tuple[str, int, int]): Port specification for OPX input
            as (controller_name, chassis_slot, port_number).
        digital_inputs (dict[str, digitalElementConfig]): Mapping of operation names
            to digital control configurations (default: empty).
        operations (dict[str, str]): Mapping of operation names to pulse config
            names (default: empty). Example: {"pi_half": "pi_half_pulse"}.
        time_of_flight (float): Signal propagation delay in nanoseconds (default: 0.0).
            Delay between when a pulse is output and when the response is received.
        sticky (bool): Whether this element retains state between operations (default: False).
            If True, the element state persists after pulse completion.
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

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Element":
        el = cls(
            name=d.get("name", ""),
            frequency=d.get("frequency", 0.0),
            analog_input=tuple(d.get("analog_input", ("con1", 1, 1))),
            analog_output=tuple(d.get("analog_output", ("con1", 1, 1))),
        )
        for name, dd in (d.get("digital_inputs") or {}).items():
            if isinstance(dd, dict):
                el.digital_inputs[name] = digitalElementConfig.from_dict(dd)
        el.operations = dict(d.get("operations") or {})
        el.time_of_flight = d.get("time_of_flight", 0.0)
        el.sticky = d.get("sticky", False)
        return el

    def __repr__(self) -> str:
        return f"<Element {self.name} freq={self.frequency} in={self.analog_input} out={self.analog_output}>"


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

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ElementConfig":
        ec = cls()
        for name, ed in (d or {}).items():
            if isinstance(ed, dict):
                ec.elements[name] = Element.from_dict(ed)
        return ec

    def __repr__(self) -> str:
        return f"<ElementConfig elements={len(self.elements)}>"
