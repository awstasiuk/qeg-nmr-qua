"""Data models for pulse sequence steps."""

from dataclasses import dataclass, field
from typing import Optional, List, Any
from enum import Enum


class StepType(Enum):
    """Types of sequence steps."""
    PULSE = "pulse"
    DELAY = "delay"
    LOOP = "loop"
    MEASURE = "measure"


@dataclass
class SequenceStep:
    """Base class for sequence steps."""
    step_type: StepType
    enabled: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        raise NotImplementedError
    
    @staticmethod
    def from_dict(data: dict) -> 'SequenceStep':
        """Create step from dictionary."""
        step_type = StepType(data['step_type'])
        if step_type == StepType.PULSE:
            return PulseStep.from_dict(data)
        elif step_type == StepType.DELAY:
            return DelayStep.from_dict(data)
        elif step_type == StepType.LOOP:
            return LoopStep.from_dict(data)
        elif step_type == StepType.MEASURE:
            return MeasureStep.from_dict(data)
        raise ValueError(f"Unknown step type: {step_type}")
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        raise NotImplementedError


@dataclass
class PulseStep(SequenceStep):
    """Represents a pulse operation."""
    pulse_name: str = "pi_half"  # e.g., "pi_half", "pi", "pi_half_x", "pi_half_y"
    element: str = "resonator"
    amplitude: Optional[float] = None  # None means use default from settings
    amplitude_sweep: bool = False  # If True, this is a sweep parameter for 2D
    sweep_start: float = 0.5
    sweep_end: float = 1.5
    sweep_points: int = 50
    phase: Optional[float] = None  # Phase offset in degrees
    duration: Optional[float] = None  # Override pulse length in ns
    
    def __post_init__(self):
        if not hasattr(self, 'step_type') or self.step_type != StepType.PULSE:
            object.__setattr__(self, 'step_type', StepType.PULSE)
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        amp_str = ""
        if self.amplitude_sweep:
            amp_str = f" [SWEEP: {self.sweep_start:.2f}-{self.sweep_end:.2f}]"
        elif self.amplitude is not None:
            amp_str = f" (amp={self.amplitude:.3f})"
        
        phase_str = f" @{self.phase}°" if self.phase is not None else ""
        
        return f"Pulse: {self.pulse_name}{amp_str}{phase_str}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'step_type': self.step_type.value,
            'enabled': self.enabled,
            'pulse_name': self.pulse_name,
            'element': self.element,
            'amplitude': self.amplitude,
            'amplitude_sweep': self.amplitude_sweep,
            'sweep_start': self.sweep_start,
            'sweep_end': self.sweep_end,
            'sweep_points': self.sweep_points,
            'phase': self.phase,
            'duration': self.duration,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'PulseStep':
        """Create from dictionary."""
        return PulseStep(
            step_type=StepType.PULSE,
            enabled=data.get('enabled', True),
            pulse_name=data.get('pulse_name', 'pi_half'),
            element=data.get('element', 'resonator'),
            amplitude=data.get('amplitude'),
            amplitude_sweep=data.get('amplitude_sweep', False),
            sweep_start=data.get('sweep_start', 0.5),
            sweep_end=data.get('sweep_end', 1.5),
            sweep_points=data.get('sweep_points', 50),
            phase=data.get('phase'),
            duration=data.get('duration'),
        )


@dataclass
class DelayStep(SequenceStep):
    """Represents a delay/wait operation."""
    duration_ns: int = 1000  # Duration in nanoseconds
    
    def __post_init__(self):
        if not hasattr(self, 'step_type') or self.step_type != StepType.DELAY:
            object.__setattr__(self, 'step_type', StepType.DELAY)
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        # Convert to appropriate units for display
        if self.duration_ns >= 1_000_000:
            return f"Delay: {self.duration_ns / 1_000_000:.2f} ms"
        elif self.duration_ns >= 1_000:
            return f"Delay: {self.duration_ns / 1_000:.2f} µs"
        else:
            return f"Delay: {self.duration_ns} ns"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'step_type': self.step_type.value,
            'enabled': self.enabled,
            'duration_ns': self.duration_ns,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'DelayStep':
        """Create from dictionary."""
        return DelayStep(
            step_type=StepType.DELAY,
            enabled=data.get('enabled', True),
            duration_ns=data.get('duration_ns', 1000),
        )


@dataclass
class LoopStep(SequenceStep):
    """Represents a loop container."""
    iterations: int = 1
    steps: List[SequenceStep] = field(default_factory=list)
    
    def __post_init__(self):
        if not hasattr(self, 'step_type') or self.step_type != StepType.LOOP:
            object.__setattr__(self, 'step_type', StepType.LOOP)
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        return f"Loop: {self.iterations}× ({len(self.steps)} steps)"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'step_type': self.step_type.value,
            'enabled': self.enabled,
            'iterations': self.iterations,
            'steps': [step.to_dict() for step in self.steps],
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'LoopStep':
        """Create from dictionary."""
        steps = [SequenceStep.from_dict(s) for s in data.get('steps', [])]
        return LoopStep(
            step_type=StepType.LOOP,
            enabled=data.get('enabled', True),
            iterations=data.get('iterations', 1),
            steps=steps,
        )


@dataclass
class MeasureStep(SequenceStep):
    """Represents a measurement operation."""
    element: str = "resonator"
    
    def __post_init__(self):
        if not hasattr(self, 'step_type') or self.step_type != StepType.MEASURE:
            object.__setattr__(self, 'step_type', StepType.MEASURE)
    
    def get_display_name(self) -> str:
        """Get display name for UI."""
        return f"Measure: {self.element}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'step_type': self.step_type.value,
            'enabled': self.enabled,
            'element': self.element,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'MeasureStep':
        """Create from dictionary."""
        return MeasureStep(
            step_type=StepType.MEASURE,
            enabled=data.get('enabled', True),
            element=data.get('element', 'resonator'),
        )
