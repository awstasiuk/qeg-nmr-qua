from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.config.controller import ControllerConfig, FEModuleConfig
from qeg_nmr_qua.config.element import Element
from qeg_nmr_qua.config.pulse import ControlPulse, MeasPulse
from qeg_nmr_qua.config.waveform import AnalogWaveformConfig, DigitalWaveform
from qeg_nmr_qua.config.integration import IntegrationWeights
from qeg_nmr_qua.config.settings import ExperimentSettings

from qualang_tools.units import unit
import numpy as np
import json
from pathlib import Path

u = unit(coerce_to_integer=True)


def cfg_from_settings(settings: ExperimentSettings) -> OPXConfig:
    """
    Create an OPXConfig object from ExperimentSettings. This function
    closesly reproduces the config_building.py example, as of 12/3/2025.
    """

    # configure the OPX with these settings
    cfg = OPXConfig(
        qop_ip="192.168.88.253",  # OPX is local to the lab computer
        cluster="lex",  # name of cluster is lex
    )

    # define the OPX controller, the LF-FEM config, and its I/O
    opx1000 = ControllerConfig(
        model="opx1000",
        controller_name="con1",
    )

    lf_fem = FEModuleConfig(
        slot=1,
        fem_type="LF",
    )
    lf_fem.add_analog_output(port=2)
    lf_fem.add_analog_input(port=1, gain_db=0)
    lf_fem.add_analog_input(port=2, gain_db=16)
    lf_fem.add_digital_output(port=1, name="readout_switch")
    lf_fem.add_digital_output(port=2, name="amplifier_blank", inverted=True)
    lf_fem.add_digital_output(port=3, name="debug_marker")

    opx1000.add_module(chasis_slot=1, module=lf_fem)
    cfg.add_controller(opx1000)

    # qua needs the elements to have operations linked to pulses and waveforms
    # new pulses need to be added to elements and defined as pulses with waveforms
    # these are a few standard operations for NMR experiments
    operations = {
        "cw": "const_pulse",
        "excitation": "excitation_pulse",
        "readout": "readout_pulse",
        "no_pulse_readout": "no_pulse_readout",
        "square_pi": "square_pi_pulse",
        # unless rotation otherwise noted, refers to pi/2 pulse
        "square": "square_pulse",
        "gaussian": "gaussian_pulse",
        "gaussian_square": "gaussian_square_pulse",
        "lowpass_square": "lowpass_square_pulse",
        "tukey": "tukey_pulse",
    }
    digital_operations = {
        "voltage_on": "voltage_on_pulse",
        "voltage_off": "voltage_off_pulse",
    }

    # this is important for later when we want to refer to the pi/2 pulse
    settings.update(square_key="square")

    # define the elements, aka, lab objects controlled by opx
    probe = Element(
        name="resonator",
        frequency=settings.rf_freq(),
        analog_input=("con1", 1, 2),
        analog_output=("con1", 1, 2),
        operations=operations,
        time_of_flight=280 * u.ns,
    )
    probe.add_digital_input(
        operation="marker",  # when control the resonator, we will also output a marker TTL
        controller_name="con1",
        chasis_slot=1,
        port_number=3,
    )
    # qua magic to do zero-delay readout. Identical to resonator
    helper = Element(
        name="helper",
        frequency=settings.rf_freq(),
        analog_input=("con1", 1, 2),
        analog_output=("con1", 1, 2),
        operations=operations,
        time_of_flight=280 * u.ns,
    )
    helper.add_digital_input(
        operation="marker",  # when control the resonator, we will also output a marker TTL
        controller_name="con1",
        chasis_slot=1,
        port_number=3,
    )
    # amplifier blanking control element
    amplifier = Element(
        name="amplifier",
        frequency=settings.rf_freq(),
        analog_input=("con1", 1, 2),
        analog_output=("con1", 1, 2),
        operations=digital_operations,
        time_of_flight=280 * u.ns,
        sticky=True,
    )
    amplifier.add_digital_input(
        operation="marker",  # when we drive the amplifier, it will be unblanked via TTL
        controller_name="con1",
        chasis_slot=1,
        port_number=2,
    )
    # reciever switch ttl control element
    # amplifier blanking control element
    rx_switch = Element(
        name="switch",
        frequency=settings.rf_freq(),
        analog_input=("con1", 1, 2),
        analog_output=("con1", 1, 2),
        operations=digital_operations,
        time_of_flight=280 * u.ns,
        sticky=True,
    )
    rx_switch.add_digital_input(
        operation="marker",  # when we drive the amplifier, it will be unblanked via TTL
        controller_name="con1",
        chasis_slot=1,
        port_number=1,
    )

    # the names of these elements is important, and will be used in the experiments
    cfg.add_element("resonator", probe)
    cfg.add_element("helper", helper)
    cfg.add_element("amplifier", amplifier)
    cfg.add_element("switch", rx_switch)

    settings.update(
        res_key="resonator",
        amp_key="amplifier",
        helper_key="helper",
        sw_key="switch",
    )

    # define the standard pulses used in NMR experiments. Links to waveforms later
    cw = ControlPulse(
        length=settings.const_len,
        waveform="const_wf",
    )
    # used for resonator spectroscopy
    readout = MeasPulse(
        length=settings.dwell_time,
        waveform="readout_wf",
        digital_marker="ON",
    )
    # needed for reasons that currently elude me
    excitation = ControlPulse(
        length=settings.excitation_length,
        waveform="excitation_wf",
        digital_marker="ON",
    )
    # used for FID measurements
    no_pulse_readout = MeasPulse(
        length=settings.dwell_time,
        waveform="zero_wf",
        digital_marker="ON",
    )
    # square pi/2 pulse
    square = ControlPulse(
        length=settings.pulse_length,
        waveform="square_wf",
        digital_marker="ON",
    )
    # square pi pulse
    square_pi = ControlPulse(
        length=2 * settings.pulse_length,
        waveform="square_wf",
        digital_marker="ON",
    )
    # Gaussian pi/2 pulse
    gaussian = ControlPulse(
        length=settings.pulse_length,
        waveform="gaussian_wf",
        digital_marker="ON",
    )
    # Gaussian square (smooth rise + flat region) pi/2 pulse
    gaussian_square = ControlPulse(
        length=settings.pulse_length,
        waveform="gaussian_square_wf",
        digital_marker="ON",
    )
    # Lowpass-approximated square pi/2 pulse
    lowpass_square = ControlPulse(
        length=settings.pulse_length, # 2x longer to account for preshoot/overshoot
        waveform="lowpass_square_wf",
        digital_marker="ON",
    )
    # Tukey window pi/2 pulse
    tukey = ControlPulse(
        length=settings.pulse_length, # 2x longer to account for preshoot/overshoot
        waveform="tukey_wf",
        digital_marker="ON",
    )

    # tll high
    voltage_on = ControlPulse(
        length=40 * u.ns,  # short, length is not important b/c sticky
        waveform="zero_wf",
        digital_marker="ON",
    )
    # ttl low
    voltage_off = ControlPulse(
        length=40 * u.ns,  # short, length is not important b/c sticky
        waveform="zero_wf",
        digital_marker="OFF",
    )

    cfg.add_pulse("const_pulse", cw)
    cfg.add_pulse("readout_pulse", readout)
    cfg.add_pulse("excitation_pulse", excitation)
    cfg.add_pulse("no_pulse_readout", no_pulse_readout)
    cfg.add_pulse("square_pulse", square)
    cfg.add_pulse("square_pi_pulse", square_pi)
    cfg.add_pulse("gaussian_pulse", gaussian)
    cfg.add_pulse("gaussian_square_pulse", gaussian_square)
    cfg.add_pulse("lowpass_square_pulse", lowpass_square)
    cfg.add_pulse("tukey_pulse", tukey)
    cfg.add_pulse("voltage_on_pulse", voltage_on)
    cfg.add_pulse("voltage_off_pulse", voltage_off)

    # define the waveforms used in the pulses above
    cfg.add_waveform("const_wf", waveform=settings.const_amp)
    cfg.add_waveform("zero_wf", waveform=0.0)
    cfg.add_waveform("readout_wf", waveform=settings.readout_amp)
    cfg.add_waveform("excitation_wf", waveform=settings.excitation_amp)
    cfg.add_waveform("square_wf", waveform=settings.pulse_amplitude)
    
    # Gaussian waveform samples for shaped pi/2 pulse out to 3 stddev
    gaussian_awg = settings.pulse_amplitude * np.exp(
        -0.5 * (np.linspace(-3, 3, settings.pulse_length) ** 2))
    cfg.add_waveform("gaussian_wf", waveform=gaussian_awg.tolist())
    
    # Gaussian square waveform samples for shaped pi/2 pulse out to 3 stddev
    gaussian_square_width = int(settings.pulse_length * settings.pulse_rise_fall / 2)
    gaussian_square_awg = settings.pulse_amplitude * np.r_[
        np.exp(-0.5 * np.linspace(-3, 0, gaussian_square_width)**2),
        np.ones(int(settings.pulse_length*(1 - settings.pulse_rise_fall))),
        np.exp(-0.5 * np.linspace(0, -3, gaussian_square_width)**2)
    ]
    cfg.add_waveform("gaussian_square_wf", waveform=gaussian_square_awg.tolist())

    # Low-pass (Butterworth-filtered) square pulse for shaped pi/2 pulse
    n_harmonics   = 30 # number of harmonics to approximate square wave
    lowpass_order  = 10 # order of oscillations
    lowpass_t = np.linspace(-.5, 1.5, settings.pulse_length) # plots the pulse from t=-0.5 to 1.5
    lowpass_square_awg = settings.pulse_amplitude * (
        0.5+(2/np.pi) * sum(
            np.sin((2*k-1)*np.pi*lowpass_t) /
            ((2*k-1) * np.sqrt(1 + ((2*k-1)/n_harmonics)**(2*lowpass_order)))
            for k in range(1, n_harmonics+1)
        )
    )
    lowpass_square_awg = np.clip(lowpass_square_awg, -0.5, 0.5)
    cfg.add_waveform("lowpass_square_wf", waveform=lowpass_square_awg.tolist())

    # Tukey windowed waveform samples for shaped pi/2 pulse
    tukey_x = np.linspace(-1, 1, settings.pulse_length)
    tukey_awg = settings.pulse_amplitude * (
        np.ones(settings.pulse_length) if settings.pulse_rise_fall == 0 else np.where(
            np.abs(tukey_x) < 1 - settings.pulse_rise_fall,
            1.0,
            0.5 * (1 + np.cos(np.pi * (np.abs(tukey_x) - 1 + settings.pulse_rise_fall) / settings.pulse_rise_fall))
        )
    )
    cfg.add_waveform("tukey_wf", waveform=tukey_awg.tolist())

    # define digital waveforms (markers)
    cfg.add_digital_waveform("ON", state=1, length=0)
    cfg.add_digital_waveform("OFF", state=0, length=0)

    # finally, define integration weights for measurement pulses
    cfg.add_integration_weight(
        name="cosine_weights",
        length=settings.dwell_time,
        real_weight=1.0,
        imag_weight=0.0,
    )
    cfg.add_integration_weight(
        name="sine_weights",
        length=settings.dwell_time,
        real_weight=0.0,
        imag_weight=1.0,
    )
    cfg.add_integration_weight(
        name="minus_sine_weights",
        length=settings.dwell_time,
        real_weight=0.0,
        imag_weight=-1.0,
    )
    cfg.add_integration_weight(
        name="rotated_cosine_weights",
        length=settings.dwell_time,
        real_weight=np.cos(np.pi * (settings.rotation_angle / 180)),
        imag_weight=np.sin(np.pi * (settings.rotation_angle / 180)),
    )
    cfg.add_integration_weight(
        name="rotated_sine_weights",
        length=settings.dwell_time,
        real_weight=-np.sin(np.pi * (settings.rotation_angle / 180)),
        imag_weight=np.cos(np.pi * (settings.rotation_angle / 180)),
    )
    cfg.add_integration_weight(
        name="rotated_minus_sine_weights",
        length=settings.dwell_time,
        real_weight=np.sin(np.pi * (settings.rotation_angle / 180)),
        imag_weight=-np.cos(np.pi * (settings.rotation_angle / 180)),
    )
    # these are placeholder for potential future loaded optimizations? seems not useful
    cfg.add_integration_weight(
        name="opt_cosine_weights",
        length=settings.dwell_time,
        real_weight=np.cos(np.pi * (settings.rotation_angle / 180)),
        imag_weight=np.sin(np.pi * (settings.rotation_angle / 180)),
    )
    cfg.add_integration_weight(
        name="sine_weights",
        length=settings.dwell_time,
        real_weight=-np.sin(np.pi * (settings.rotation_angle / 180)),
        imag_weight=np.cos(np.pi * (settings.rotation_angle / 180)),
    )
    cfg.add_integration_weight(
        name="opt_minus_sine_weights",
        length=settings.dwell_time,
        real_weight=np.sin(np.pi * (settings.rotation_angle / 180)),
        imag_weight=-np.cos(np.pi * (settings.rotation_angle / 180)),
    )

    return cfg
