import tempfile
from pathlib import Path
import json

from qeg_nmr_qua.config.config import OPXConfig
from qeg_nmr_qua.config.element import Element


def test_opxconfig_save_and_load_roundtrip():
    opx = OPXConfig()

    # add example content
    elm = Element(
        name="probe",
        frequency=376.5e6,
        analog_input=("con1", 1, 1),
        analog_output=("con1", 1, 1),
    )
    opx.add_element("probe", elm)

    opx.pulses.add_control_pulse("pi", length=1000, waveform="pi_wf")
    opx.add_waveform("pi_wf", 0.5)
    opx.add_digital_waveform("marker1", state=1, length=100)
    opx.add_integration_weight("w1", length=1000, real_weight=1.0, imag_weight=0.0)

    # save to temp file
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "opx_config.json"
        opx.save_to_file(str(path))
        assert path.exists()

        # read raw json and ensure keys present
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        assert "elements" in raw
        assert "pulses" in raw

        # load back
        loaded = OPXConfig.load_from_file(str(path))

        # compare dicts
        assert loaded.to_dict() == opx.to_dict()
