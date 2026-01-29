import qeg_nmr_qua as qnmr
from calibrations import (
    phase_calibration,
    check_offset,
    bisection_offset_calibration,
    pulse_amp_calibration,
)

from qualang_tools.units import unit
from pathlib import Path
import matplotlib.pyplot as plt

u = unit(coerce_to_integer=True)

# Enable interactive plotting mode for responsive plots
plt.ion()

# create base settings object for experiments
settings = qnmr.ExperimentSettings(
    n_avg=4,
    pulse_length=1.1 * u.us,
    pulse_amplitude=0.45,  # amplitude is 0.5*Vpp
    pulse_shape="pi_half",
    rotation_angle=239.8,  # degrees
    thermal_reset=4 * u.s,
    center_freq=282.1901 * u.MHz,
    offset_freq=6350 * u.Hz,
    readout_delay=20 * u.us,
    dwell_time=4 * u.us,
    readout_start=0 * u.us,
    readout_end=256 * u.us,
    save_dir=Path(__file__).parent / "test_results",
)

saver = qnmr.DataSaver(settings.save_dir)
saver.save_settings(settings, "autocal_settings", overwrite=True)

phase_calibration(settings)
print(
    f"[AUTOCAL] After phase_calibration: rotation_angle = {settings.rotation_angle:.2f}°"
)
saver.save_settings(settings, "autocal_settings", overwrite=True)

if check_offset(settings) != 0:
    success = bisection_offset_calibration(settings)
    print(
        f"[AUTOCAL] After offset calibration: offset_freq = {settings.offset_freq:.2f} Hz"
    )
else:
    success = True
    print(
        f"[AUTOCAL] Offset already calibrated: offset_freq = {settings.offset_freq:.2f} Hz"
    )

if success:
    # calibrate pulse power
    settings.n_avg = 4
    saver.save_settings(settings, "autocal_settings", overwrite=True)

    pulse_amp_calibration(settings, n_wraps=2)
    print(
        f"[AUTOCAL] After 1st pulse cal (2 wraps): pulse_amplitude = {settings.pulse_amplitude:.4f}"
    )
    saver.save_settings(settings, "autocal_settings", overwrite=True)

    pulse_amp_calibration(settings, n_wraps=3)
    print(
        f"[AUTOCAL] After 2nd pulse cal (3 wraps): pulse_amplitude = {settings.pulse_amplitude:.4f}"
    )
    saver.save_settings(settings, "autocal_settings", overwrite=True)

    pulse_amp_calibration(settings, n_wraps=2)
    print(
        f"[AUTOCAL] After 3rd pulse cal (2 wraps): pulse_amplitude = {settings.pulse_amplitude:.4f}"
    )
    saver.save_settings(settings, "autocal_settings", overwrite=True)
