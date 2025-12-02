from dataclasses import dataclass, field

from typing import Any, Dict, Optional, Type, TypeVar


@dataclass
class IntegrationWeightMapping:
    cos: str = "cosine_weights"
    sin: str = "sine_weights"
    minus_sin: str = "minus_sine_weights"
    rotated_cos: str = "rotated_cosine_weights"
    rotated_sin: str = "rotated_sine_weights"
    rotated_minus_sin: str = "rotated_minus_sine_weights"
    opt_cos: str = "opt_cosine_weights"
    opt_sin: str = "opt_sine_weights"
    opt_minus_sin: str = "opt_minus_sine_weights"

    def to_dict(self) -> Dict[str, str]:
        return {
            "cos": self.cos,
            "sin": self.sin,
            "minus_sin": self.minus_sin,
            "rotated_cos": self.rotated_cos,
            "rotated_sin": self.rotated_sin,
            "rotated_minus_sin": self.rotated_minus_sin,
            "opt_cos": self.opt_cos,
            "opt_sin": self.opt_sin,
            "opt_minus_sin": self.opt_minus_sin,
        }

    def to_opx_config(self) -> Dict[str, str]:
        return self.to_dict()

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "IntegrationWeightMapping":
        if not isinstance(d, dict):
            return cls()
        return cls(
            cos=d.get("cos", "cosine_weights"),
            sin=d.get("sin", "sine_weights"),
            minus_sin=d.get("minus_sin", "minus_sine_weights"),
            rotated_cos=d.get("rotated_cos", "rotated_cosine_weights"),
            rotated_sin=d.get("rotated_sin", "rotated_sine_weights"),
            rotated_minus_sin=d.get("rotated_minus_sin", "rotated_minus_sine_weights"),
            opt_cos=d.get("opt_cos", "opt_cosine_weights"),
            opt_sin=d.get("opt_sin", "opt_sine_weights"),
            opt_minus_sin=d.get("opt_minus_sin", "opt_minus_sine_weights"),
        )

    def __repr__(self) -> str:
        return f"<IntegrationWeightMapping cos={self.cos} sin={self.sin} opt_cos={self.opt_cos}>"


@dataclass
class IntegrationWeight:
    """
    Configuration for a single integration weight set.
    """

    length: int = 0  # in nanoseconds
    real_weight: float = 1
    imag_weight: float = 0

    def to_opx_config(self) -> Dict[str, Any]:
        return {
            "cosine": [(self.real_weight, self.length)],
            "sine": [(self.imag_weight, self.length)],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "length": self.length,
            "real_weight": self.real_weight,
            "imag_weight": self.imag_weight,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationWeight":
        return cls(
            length=d.get("length", 0),
            real_weight=d.get("real_weight", 1),
            imag_weight=d.get("imag_weight", 0),
        )

    def __repr__(self) -> str:
        return f"<IntegrationWeight len={self.length} real={self.real_weight} imag={self.imag_weight}>"


@dataclass
class IntegrationWeights:
    """
    Configuration for integration weights used in measurements.
    """

    weights: dict[str, IntegrationWeight] = field(default_factory=dict)

    def add_weight(
        self, name: str, length: int, real_weight: float = 1, imag_weight: float = 0
    ) -> None:
        """
        Add an integration weight set to the configuration.
        """
        self.weights[name] = IntegrationWeight(
            length=length, real_weight=real_weight, imag_weight=imag_weight
        )

    def to_dict(self) -> Dict[str, Any]:
        return {name: weight.to_dict() for name, weight in self.weights.items()}

    def to_opx_config(self) -> Dict[str, Any]:
        return {name: weight.to_opx_config() for name, weight in self.weights.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "IntegrationWeights":
        iw = cls()
        for name, wd in (d or {}).items():
            if isinstance(wd, dict):
                iw.weights[name] = IntegrationWeight.from_dict(wd)
        return iw

    def __repr__(self) -> str:
        return f"<IntegrationWeights sets={len(self.weights)}>"
