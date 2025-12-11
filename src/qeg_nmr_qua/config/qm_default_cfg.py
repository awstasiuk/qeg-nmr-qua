"""
4+2 LF-FEM configuration for OPX1000

WARNING: EXCITATION, PI, PI_HALF PULSES HAVE DIGITAL MARKERS WHICH WILL TRIGGER AMPLIFIER

"""

from pathlib import Path
from qualang_tools.config.waveform_tools import drag_gaussian_pulse_waveforms
import numpy as np
from qualang_tools.units import unit

u = unit(coerce_to_integer=True)

con = "con1"  # Controller name in OPX1000
lf_fem = 1  # Where is it in OPX1000
sampling_rate = int(1e9)  # or, int(2e9)

default_additional_files = {
    Path(__file__).name: Path(__file__).name,
}

####################################
# %% ---- Resonator parameters ---- #
####################################
readout_key = "resonator"
offset_freq = 1450 * u.Hz  # DAC/ADC offset frequency
resonator_frequency = (
    282.1901 * u.MHz - offset_freq
)  # Rotating frame frequency of spins
print(f"I/O frequency set to {resonator_frequency/u.MHz:.10f} MHz")
resonator_IF = resonator_frequency
spin_relaxation = 4 * u.s  # 5*T1
resonator_relaxation = 250 * u.us

# Input/output connections (all 2s - 2hollis)
resonator_analogOutput = (con, lf_fem, 2)  # Controller, FEM, AO channel
resonator_analogInput = (con, lf_fem, 2)  # Controller, FEM, AI channel
resonator_digitalOutput = (
    con,
    lf_fem,
    3,
)  # Controller, FEM, DO channel - for scope trigger
switch_digitalOutput = (
    con,
    lf_fem,
    1,
)  # Controller, FEM, DO channel - switch LVTTL plays to this port
amplifier_digitalOutput = (
    con,
    lf_fem,
    2,
)  # Controller, FEM, DO channel - amplifier LVTTL plays to this port
time_of_flight = 280  # ns

################################
# %% ---- Pulse parameters ---- #
################################
# Excitation
excitation_len = 5 * u.us
excitation_amp = 0.03
# Square pi pulse
square_pi_half_len = 1.1 * u.us
# square_pi_half_amp = 0.2235
square_pi_half_amp = 0.42

# Gaussian pi/2 pulse
gaussian_pi_half_len = 1.776 * u.us
gaussian_pi_half_amp = 0.2
gaussian_pi_half_samples = gaussian_pi_half_amp * np.exp(
    -0.5 * (np.linspace(-3, 3, gaussian_pi_half_len) ** 2)
)
# Constant pulse parameters
const_len = 100
const_amp = 0.03

# Digital marker
marker_delay = 0
marker_buffer = 0

# Readout optimization
readout_len = 4 * u.us  # dwell time for demodulation and integration of NMR signal
readout_delay = 20 * u.us  # time before closing Rx switch after measure pulse
readout_amp = 0.01
rotation_angle = (250 / 180) * np.pi
ge_thresholds = 0.0

# macro delays
drive_mode_delay = 730 * 4 * u.ns
readout_mode_delay = 710 * 4 * u.ns
safe_mode_delay = 240 * 4 * u.ns

# Adjust readout time to account for macro delays, in clock cycles
readout = (readout_delay - safe_mode_delay - readout_mode_delay) // 4
assert (
    readout > 16
), "Readout delay too short. Increase readout_delay or reduce macro delays."

# load default waits, we are not changing them here
opt_weights_real = [(np.cos(rotation_angle), readout_len)]
opt_weights_minus_imag = [(np.sin(rotation_angle), readout_len)]
opt_weights_imag = [(-np.sin(rotation_angle), readout_len)]
opt_weights_minus_real = [(-np.cos(rotation_angle), readout_len)]


# %% ---- Config ---- #
config = {
    "controllers": {
        con: {
            "type": "opx1000",
            "fems": {
                # declaring MW-FEM for qubit control and resonator readout
                lf_fem: {
                    "type": "LF",
                    "analog_outputs": {
                        2: {
                            "offset": 0.0,
                            "sampling_rate": sampling_rate,
                            "output_mode": "direct",
                        },  # input to the resonator line
                    },
                    "analog_inputs": {
                        1: {
                            "offset": 0.0,
                            "gain_db": 0,
                            "sampling_rate": sampling_rate,
                        },  # output of resonator line
                        2: {
                            "offset": 0.0,
                            "gain_db": 16,
                            "sampling_rate": sampling_rate,
                        },  # output of resonator line
                    },
                    "digital_outputs": {
                        1: {},
                        2: {"inverted": True},
                        3: {},
                        4: {},
                    },
                },
            },
        }
    },
    "elements": {
        "resonator": {
            "singleInput": {
                "port": resonator_analogOutput,
            },
            "intermediate_frequency": resonator_IF,
            "outputs": {
                "out1": resonator_analogInput,
            },
            "digitalInputs": {
                "marker": {
                    "port": resonator_digitalOutput,
                    "delay": marker_delay,
                    "buffer": marker_buffer,
                }
            },
            "operations": {
                "cw": "const_pulse",
                "excitation": "excitation_pulse",
                "readout": "readout_pulse",
                "no_pulse_readout": "no_pulse_readout",
                "pi": "pi_half_pulse",
                "pi_half": "pi_half_pulse",
                "gaussian_pi_half": "gaussian_pi_half_pulse",
            },
            "time_of_flight": time_of_flight,
        },
        "helper": {
            "singleInput": {
                "port": resonator_analogOutput,
            },
            "intermediate_frequency": resonator_IF,
            "outputs": {
                "out1": resonator_analogInput,
            },
            "digitalInputs": {
                "marker": {
                    "port": resonator_digitalOutput,
                    "delay": marker_delay,
                    "buffer": marker_buffer,
                }
            },
            "operations": {
                "cw": "const_pulse",
                "excitation": "excitation_pulse",
                "readout": "readout_pulse",
                "no_pulse_readout": "no_pulse_readout",
                "pi": "pi_half_pulse",
                "pi_half": "pi_half_pulse",
                "gaussian_pi_half": "gaussian_pi_half_pulse",
            },
            "time_of_flight": time_of_flight,
        },
        "amplifier": {
            "singleInput": {
                "port": resonator_analogOutput,
            },
            "intermediate_frequency": resonator_IF,
            "outputs": {
                "out1": resonator_analogInput,
            },
            "sticky": {
                "analog": True,
                "digital": True,
            },
            "digitalInputs": {
                "marker": {
                    "port": amplifier_digitalOutput,
                    "delay": 0,
                    "buffer": 0,
                }
            },
            "operations": {
                "voltage_on": "voltage_on_pulse",
                "voltage_off": "voltage_off_pulse",
            },
            "time_of_flight": time_of_flight,
        },
        "switch": {
            "singleInput": {
                "port": resonator_analogOutput,
            },
            "intermediate_frequency": resonator_IF,
            "outputs": {
                "out1": resonator_analogInput,
            },
            "sticky": {
                "analog": True,
                "digital": True,
            },
            "digitalInputs": {
                "marker": {
                    "port": switch_digitalOutput,
                    "delay": 0,
                    "buffer": 0,
                }
            },
            "operations": {
                "voltage_on": "voltage_on_pulse",
                "voltage_off": "voltage_off_pulse",
            },
            "time_of_flight": time_of_flight,
        },
    },
    "pulses": {
        "const_pulse": {
            "operation": "control",
            "length": const_len,
            "waveforms": {
                "single": "const_wf",
            },
        },
        "readout_pulse": {
            "operation": "measurement",
            "length": readout_len,
            "waveforms": {
                "single": "readout_wf",
            },
            "integration_weights": {
                "cos": "cosine_weights",
                "sin": "sine_weights",
                "minus_sin": "minus_sine_weights",
                "rotated_cos": "rotated_cosine_weights",
                "rotated_sin": "rotated_sine_weights",
                "rotated_minus_sin": "rotated_minus_sine_weights",
                "opt_cos": "opt_cosine_weights",
                "opt_sin": "opt_sine_weights",
                "opt_minus_sin": "opt_minus_sine_weights",
            },
            "digital_marker": "ON",
        },
        "no_pulse_readout": {
            "operation": "measurement",
            "length": readout_len,
            "waveforms": {
                "single": "zero_wf",
            },
            "integration_weights": {
                "cos": "cosine_weights",
                "sin": "sine_weights",
                "minus_sin": "minus_sine_weights",
                "rotated_cos": "rotated_cosine_weights",
                "rotated_sin": "rotated_sine_weights",
                "rotated_minus_sin": "rotated_minus_sine_weights",
                "opt_cos": "opt_cosine_weights",
                "opt_sin": "opt_sine_weights",
                "opt_minus_sin": "opt_minus_sine_weights",
            },
            "digital_marker": "ON",
        },
        "excitation_pulse": {
            "operation": "control",
            "length": excitation_len,
            "waveforms": {
                "single": "excitation_wf",
            },
            "digital_marker": "ON",
        },
        "pi_pulse": {
            "operation": "control",
            "length": square_pi_half_len * 2,
            "waveforms": {
                "single": "square_pi_wf",
            },
            "digital_marker": "ON",
        },
        "pi_half_pulse": {
            "operation": "control",
            "length": square_pi_half_len,
            "waveforms": {
                "single": "square_pi_half_wf",
            },
            "digital_marker": "ON",
        },
        "gaussian_pi_half_pulse": {
            "operation": "control",
            "length": gaussian_pi_half_len,
            "waveforms": {
                "single": "gaussian_pi_half_wf",
            },
            "digital_marker": "ON",
        },
        "voltage_on_pulse": {
            "operation": "control",
            "length": 40,
            "waveforms": {
                "single": "zero_wf",
            },
            "digital_marker": "ON",
        },
        "voltage_off_pulse": {
            "operation": "control",
            "length": 40,
            "waveforms": {
                "single": "zero_wf",
            },
            "digital_marker": "OFF",
        },
    },
    "waveforms": {
        "const_wf": {"type": "constant", "sample": const_amp},
        "zero_wf": {"type": "constant", "sample": 0.0},
        "readout_wf": {"type": "constant", "sample": readout_amp},
        "excitation_wf": {"type": "constant", "sample": excitation_amp},
        "square_pi_wf": {"type": "constant", "sample": square_pi_half_amp},
        "square_pi_half_wf": {"type": "constant", "sample": square_pi_half_amp},
        "gaussian_pi_half_wf": {
            "type": "arbitrary",
            "samples": gaussian_pi_half_samples,
        },
    },
    "digital_waveforms": {
        "ON": {"samples": [(1, 0)]},
        "OFF": {"samples": [(0, 0)]},
    },
    "integration_weights": {
        "cosine_weights": {
            "cosine": [(1.0, readout_len)],
            "sine": [(0.0, readout_len)],
        },
        "sine_weights": {
            "cosine": [(0.0, readout_len)],
            "sine": [(1.0, readout_len)],
        },
        "minus_sine_weights": {
            "cosine": [(0.0, readout_len)],
            "sine": [(-1.0, readout_len)],
        },
        "rotated_cosine_weights": {
            "cosine": [(np.cos(rotation_angle), readout_len)],
            "sine": [(np.sin(rotation_angle), readout_len)],
        },
        "rotated_sine_weights": {
            "cosine": [(-np.sin(rotation_angle), readout_len)],
            "sine": [(np.cos(rotation_angle), readout_len)],
        },
        "rotated_minus_sine_weights": {
            "cosine": [(np.sin(rotation_angle), readout_len)],
            "sine": [(-np.cos(rotation_angle), readout_len)],
        },
        "opt_cosine_weights": {
            "cosine": opt_weights_real,
            "sine": opt_weights_minus_imag,
        },
        "opt_sine_weights": {
            "cosine": opt_weights_imag,
            "sine": opt_weights_real,
        },
        "opt_minus_sine_weights": {
            "cosine": opt_weights_minus_imag,
            "sine": opt_weights_minus_real,
        },
    },
}
