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
    sampling_rate: int = 1_000_000_000  # 1e9
    output_mode: str = "direct"

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "sampling_rate": self.sampling_rate,
            "output_mode": self.output_mode,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AnalogOutput":
        return cls(
            offset=d.get("offset", 0.0),
            sampling_rate=d.get("sampling_rate", 1_000_000_000),
            output_mode=d.get("output_mode", "direct"),
        )

    def to_opx_config(self) -> dict[str, Any]:
        return self.to_dict()

    def __repr__(self) -> str:  # concise one-line description
        return f"<AnalogOutput offset={self.offset} samp={self.sampling_rate} mode={self.output_mode}>"


@dataclass
class AnalogInput:
    """Configuration for an analog input channel."""

    offset: float = 0.0
    gain_db: float = 0.0
    sampling_rate: int = int(1e9)

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": self.offset,
            "gain_db": self.gain_db,
            "sampling_rate": self.sampling_rate,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AnalogInput":
        return cls(
            offset=d.get("offset", 0.0),
            gain_db=d.get("gain_db", 0.0),
            sampling_rate=d.get("sampling_rate", 1e9),
        )

    def to_opx_config(self) -> dict[str, Any]:
        return self.to_dict()

    def __repr__(self) -> str:
        return f"<AnalogInput offset={self.offset} gain_db={self.gain_db} samp={self.sampling_rate}>"


@dataclass
class DigitalIO:
    """Configuration for digital input/output."""

    name: str = "TTL"
    direction: str = "output"  # 'input' or 'output'
    inverted: bool = False  # Default i/o state is 0 (not inverted)

    def to_opx_config(self) -> dict[str, Any]:
        return {"inverted": self.inverted} if self.inverted else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "inverted": self.inverted,
        }

    def __repr__(self) -> str:
        return f"<DigitalIO {self.name} dir={self.direction} inv={self.inverted}>"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DigitalIO":
        return cls(
            name=d.get("name", "TTL"),
            direction=d.get("direction", "output"),
            inverted=d.get("inverted", False),
        )


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

    def add_digital_output(
        self, port: int, name: str = "TTL", inverted: bool = False
    ) -> None:
        """Add a digital output channel configuration."""

        assert 1 <= port <= 8, "Digital output port must be between 1 and 8."
        if port in self.digital_outputs:
            raise Warning(
                f"Digital output port {port} is already configured. Overwriting."
            )
        self.digital_outputs[port] = DigitalIO(
            name=name, direction="output", inverted=inverted
        )

    def add_analog_output(
        self,
        port: int,
        offset: float = 0.0,
        sampling_rate: int = int(1e9),
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
        sampling_rate: int = int(1e9),
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

    def to_opx_config(self) -> dict[str, Any]:
        return {
            "type": self.fem_type,
            "analog_outputs": {
                port: ao.to_opx_config() for port, ao in self.analog_outputs.items()
            },
            "analog_inputs": {
                port: ai.to_opx_config() for port, ai in self.analog_inputs.items()
            },
            "digital_outputs": {
                port: do.to_opx_config() for port, do in self.digital_outputs.items()
            },
            # "digital_inputs": {
            #     port: di.to_opx_config() for port, di in self.digital_inputs.items()
            # },
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
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

    def __repr__(self) -> str:
        ao = len(self.analog_outputs)
        ai = len(self.analog_inputs)
        do = len(self.digital_outputs)
        return (
            f"<FEModule slot={self.slot} type={self.fem_type} AO={ao} AI={ai} DO={do}>"
        )

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FEModuleConfig":
        fm = cls(slot=d.get("slot", 1), fem_type=d.get("type", "LF"))
        for port, ao in (d.get("analog_outputs") or {}).items():
            try:
                fm.analog_outputs[int(port)] = AnalogOutput.from_dict(ao)
            except Exception:
                pass
        for port, ai in (d.get("analog_inputs") or {}).items():
            try:
                fm.analog_inputs[int(port)] = AnalogInput.from_dict(ai)
            except Exception:
                pass
        for port, do in (d.get("digital_outputs") or {}).items():
            try:
                fm.digital_outputs[int(port)] = DigitalIO.from_dict(do)
            except Exception:
                pass
        return fm


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

    def to_opx_config(self) -> dict[str, Any]:
        return {
            self.controller_name: {
                "type": self.model,
                "fems": {
                    slot: module.to_opx_config()
                    for slot, module in self.modules.items()
                },
            }
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "controller_name": self.controller_name,
            "modules": {
                slot: module.to_dict() for slot, module in self.modules.items()
            },
        }

    def __repr__(self) -> str:
        return f"<Controller {self.controller_name} model={self.model} modules={len(self.modules)}>"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ControllerConfig":
        cc = cls(
            model=d.get("model", "opx1000"),
            controller_name=d.get("controller_name", "con1"),
        )
        for slot, md in (d.get("modules") or {}).items():
            try:
                cc.modules[int(slot)] = FEModuleConfig.from_dict(md)
            except Exception:
                pass
        return cc
