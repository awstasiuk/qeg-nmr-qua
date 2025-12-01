"""
OPX-1000 Controller Configuration Module.

This module provides configuration utilities for the OPX-1000 LF-FEM
for solid state NMR experiments.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalogOutput:
    """Configuration for an analog output channel."""

    offset: float = 0.0
    sampling_rate: float = 1e9
    output_mode: str = "direct"

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "sampling_rate": self.sampling_rate,
            "output_mode": self.output_mode,
        }


@dataclass
class AnalogInput:
    """Configuration for an analog input channel."""

    offset: float = 0.0
    gain_db: float = 0.0
    sampling_rate: float = 1e9

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "gain_db": self.gain_db,
            "sampling_rate": self.sampling_rate,
        }


@dataclass
class DigitalIO:
    """Configuration for digital input/output."""

    direction: str = "output"  # 'input' or 'output'
    inverted: bool = False  # Default i/o state is 0 (not inverted)

    def to_dict(self) -> dict[str, Any]:
        return {"inverted": self.inverted} if self.inverted else {}


@dataclass
class FEModuleConfig:
    """Configuration for the OPX-1000 controller."""

    # name: str = "con1" # controller name in OPX config
    slot: int = 1  # physical slot number in chasis
    fem_type: str = "LF"  # Low Frequency Front-End Module
    analog_outputs: dict[int, AnalogOutput] = field(default_factory=dict)
    analog_inputs: dict[int, AnalogInput] = field(default_factory=dict)
    digital_outputs: dict[int, DigitalIO] = field(default_factory=dict)
    # digital_inputs: dict[int, DigitalIO] = field(
    #     default_factory=dict
    # )  # not used currently

    def add_digital_output(self, port: int, inverted: bool = False) -> None:
        """Add a digital output channel configuration."""

        assert 1 <= port <= 8, "Digital output port must be between 1 and 8."
        if port in self.digital_outputs:
            raise Warning(
                f"Digital output port {port} is already configured. Overwriting."
            )
        self.digital_outputs[port] = DigitalIO(direction="output", inverted=inverted)

    def add_analog_output(
        self,
        port: int,
        offset: float = 0.0,
        sampling_rate: float = 1e9,
        output_mode: str = "direct",
    ) -> None:
        """Add an analog output channel configuration."""

        assert port == 1 or port == 2, "Analog output port must be 1 or 2."
        if port in self.analog_outputs:
            raise Warning(
                f"Analog output port {port} is already configured. Overwriting."
            )
        self.analog_outputs[port] = AnalogOutput(
            offset=offset, sampling_rate=sampling_rate, output_mode=output_mode
        )

    def add_analog_input(
        self,
        port: int,
        offset: float = 0.0,
        gain_db: float = 0.0,
        sampling_rate: float = 1e9,
    ) -> None:
        """Add an analog input channel configuration."""

        assert port == 1 or port == 2, "Analog input port must be 1 or 2."
        if port in self.analog_inputs:
            raise Warning(
                f"Analog input port {port} is already configured. Overwriting."
            )
        self.analog_inputs[port] = AnalogInput(
            offset=offset, gain_db=gain_db, sampling_rate=sampling_rate
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.fem_type,
            "analog_outputs": {
                port: ao.to_dict() for port, ao in self.analog_outputs.items()
            },
            "analog_inputs": {
                port: ai.to_dict() for port, ai in self.analog_inputs.items()
            },
            "digital_outputs": {
                port: do.to_dict() for port, do in self.digital_outputs.items()
            },
            # "digital_inputs": {
            #     port: di.to_dict() for port, di in self.digital_inputs.items()
            # },
        }


@dataclass
class ControllerConfig:
    """Overall OPX Chassis configuration."""

    model: str = "opx1000"
    controller_name: str = "con1"
    modules: dict[int, FEModuleConfig] = field(
        default_factory=dict
    )  # this could support multiple modules in future

    def add_module(self, chasis_slot: int, module: FEModuleConfig) -> None:
        """Add a front-end module configuration."""
        self.modules[chasis_slot] = module

    def to_dict(self) -> dict[str, Any]:
        return {
            self.controller_name: {
                "type": self.model,
                "fems": {
                    slot: module.to_dict() for slot, module in self.modules.items()
                },
            }
        }
