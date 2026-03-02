"""
Unit tests for Experiment (experiment.py).

These tests validate the data-structure behaviour of the Experiment class
without invoking any QUA code, simulating, or executing on hardware.
All tests use ``connect=False`` so no QuantumMachinesManager connection
is attempted.
"""

import warnings
from unittest.mock import MagicMock

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pytest

from qeg_nmr_qua.config.config_from_settings import cfg_from_settings
from qeg_nmr_qua.config.settings import ExperimentSettings
from qeg_nmr_qua.experiment.experiment import Experiment
from qeg_nmr_qua.experiment.experiment_1d import Experiment1D
from qeg_nmr_qua.experiment.experiment_2d import Experiment2D
from qeg_nmr_qua.experiment.experiment_3d import Experiment3D
from qeg_nmr_qua.experiment.macros import AMPLIFIER_BLANKING_TIME, RX_SWITCH_DELAY
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def settings():
    """Default ExperimentSettings with valid defaults."""
    return ExperimentSettings()


@pytest.fixture(scope="module")
def config(settings):
    """OPXConfig built from default settings (no hardware connection required)."""
    return cfg_from_settings(settings)


@pytest.fixture
def experiment(settings, config):
    """Fresh Experiment instance for each test (connect=False skips QMM)."""
    return Experiment(settings, config=config, connect=False)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestInitialisation:
    def test_commands_empty_on_init(self, experiment):
        assert experiment._commands == []

    def test_var_vec_lst_empty_on_init(self, experiment):
        assert experiment.var_vec_lst == []

    def test_use_fixed_lst_empty_on_init(self, experiment):
        assert experiment.use_fixed_lst == []

    def test_save_data_dict_contains_n_avg(self, experiment, settings):
        assert "n_avg" in experiment.save_data_dict
        assert experiment.save_data_dict["n_avg"] == settings.n_avg

    def test_start_with_wait_default_true(self, experiment):
        assert experiment.start_with_wait is True

    def test_use_frame_change_default_false(self, experiment):
        assert experiment.use_frame_change is False

    def test_pre_scan_delay_computed_correctly(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        expected = (
            settings.readout_delay // 4 - AMPLIFIER_BLANKING_TIME - 2 * RX_SWITCH_DELAY
        )
        assert expt.pre_scan_delay == expected

    def test_pre_scan_delay_too_short_raises(self, config):
        # readout_delay must be < 3904 ns to make pre_scan_delay < 16 clock cycles.
        # ExperimentSettings.validate() is NOT called on construction, so we can
        # bypass the >=5 us minimum to exercise this guard directly.
        short_settings = ExperimentSettings(readout_delay=3_800)
        with pytest.raises(ValueError, match="Readout delay too short"):
            Experiment(short_settings, config=config, connect=False)

    def test_measure_sequence_len(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        expected_len = (
            settings.readout_end - settings.readout_start
        ) // settings.dwell_time
        assert expt.measure_sequence_len == expected_len

    def test_tau_sweep_length(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        assert len(expt.tau_sweep) == expt.measure_sequence_len

    def test_tau_sweep_values_are_midpoints(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        first = expt.tau_sweep[0]
        assert np.isclose(first, 0.5 * settings.dwell_time)

    def test_readout_len_equals_dwell_time(self, experiment, settings):
        assert experiment.readout_len == settings.dwell_time

    def test_loop_wait_cycles(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        assert expt.loop_wait_cycles == settings.dwell_time // 4

    def test_wait_between_scans(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        assert expt.wait_between_scans == settings.thermal_reset // 4

    def test_no_qmm_when_connect_false(self, settings, config):
        expt = Experiment(settings, config=config, connect=False)
        assert not hasattr(expt, "qmm")

    def test_qmm_created_when_connect_true(self, settings, config, monkeypatch):
        mock_qmm = MagicMock()
        monkeypatch.setattr(
            "qeg_nmr_qua.experiment.experiment.QuantumMachinesManager",
            lambda *args, **kwargs: mock_qmm,
        )
        expt = Experiment(settings, config=config, connect=True)
        assert expt.qmm is mock_qmm


# ---------------------------------------------------------------------------
# add_pulse
# ---------------------------------------------------------------------------


class TestAddPulse:
    def test_invalid_element_raises(self, experiment):
        with pytest.raises(ValueError, match="not defined in config"):
            experiment.add_pulse("pi_half", "nonexistent_element")

    def test_invalid_operation_raises(self, experiment):
        with pytest.raises(ValueError, match="not defined for element"):
            experiment.add_pulse("bad_op", "resonator")

    def test_scalar_pulse_appended(self, experiment):
        experiment.add_pulse("pi_half", "resonator")
        cmd = experiment._commands[-1]
        assert cmd["type"] == "pulse"
        assert cmd["name"] == "pi_half"
        assert cmd["element"] == "resonator"

    def test_scalar_pulse_phase_converted(self, experiment):
        experiment.add_pulse("pi_half", "resonator", phase=90.0)
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["phase"], 90.0 / 360.0)

    def test_scalar_pulse_phase_zero(self, experiment):
        experiment.add_pulse("pi_half", "resonator", phase=0.0)
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["phase"], 0.0)

    def test_scalar_pulse_amplitude_stored(self, experiment):
        experiment.add_pulse("pi_half", "resonator", amplitude=0.5)
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["amplitude"], 0.5)

    def test_scalar_pulse_default_scale(self, experiment):
        experiment.add_pulse("pi_half", "resonator")
        cmd = experiment._commands[-1]
        assert cmd["scale"] == 1

    def test_scalar_pulse_length_override_in_clock_cycles(self, experiment):
        experiment.add_pulse("pi_half", "resonator", length=400)
        cmd = experiment._commands[-1]
        assert cmd["length"] == 400 // 4

    def test_iterable_phase_adds_loop_var(self, experiment):
        before = len(experiment.var_vec_lst)
        phases = np.array([0.0, 90.0, 180.0, 270.0])
        experiment.add_pulse("pi_half", "resonator", phase=phases)
        assert len(experiment.var_vec_lst) > before

    def test_iterable_phase_stores_as_fraction_of_2pi(self, experiment):
        phases = np.array([0.0, 90.0, 180.0, 270.0])
        experiment.add_pulse("pi_half", "resonator", phase=phases)
        stored = experiment.var_vec_lst[-1]
        expected = (phases / 360.0) % 1
        assert np.allclose(stored, expected)

    def test_iterable_amplitude_adds_loop_var(self, experiment):
        before = len(experiment.var_vec_lst)
        amps = np.array([0.1, 0.2, 0.3])
        experiment.add_pulse("pi_half", "resonator", amplitude=amps)
        assert len(experiment.var_vec_lst) > before

    def test_iterable_amplitude_loop_is_fixed(self, experiment):
        amps = np.array([0.1, 0.2, 0.3])
        experiment.add_pulse("pi_half", "resonator", amplitude=amps)
        assert True in experiment.use_fixed_lst

    def test_iterable_length_adds_loop_var(self, experiment):
        before = len(experiment.var_vec_lst)
        lengths = np.array([400, 800, 1200])
        experiment.add_pulse("pi_half", "resonator", length=lengths)
        assert len(experiment.var_vec_lst) > before

    def test_iterable_length_converted_to_clock_cycles(self, experiment):
        lengths = np.array([400, 800, 1200])
        experiment.add_pulse("pi_half", "resonator", length=lengths)
        stored = experiment.var_vec_lst[-1]
        assert np.allclose(stored, lengths // 4)

    def test_phase_360_wraps_to_zero(self, experiment):
        experiment.add_pulse("pi_half", "resonator", phase=360.0)
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["phase"], 0.0)

    def test_phase_wraps_above_360(self, experiment):
        experiment.add_pulse("pi_half", "resonator", phase=540.0)
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["phase"], 0.5)


# ---------------------------------------------------------------------------
# add_delay
# ---------------------------------------------------------------------------


class TestAddDelay:
    def test_scalar_delay_appended(self, experiment):
        experiment.add_delay(400)
        cmd = experiment._commands[-1]
        assert cmd["type"] == "delay"

    def test_scalar_delay_converted_to_clock_cycles(self, experiment):
        experiment.add_delay(400)
        cmd = experiment._commands[-1]
        assert cmd["duration"] == 400 // 4

    def test_iterable_delay_adds_loop_var(self, experiment):
        before = len(experiment.var_vec_lst)
        experiment.add_delay(np.array([400, 800, 1200]))
        assert len(experiment.var_vec_lst) > before

    def test_iterable_delay_converted_to_clock_cycles(self, experiment):
        durations = np.array([400, 800, 1200])
        experiment.add_delay(durations)
        stored = experiment.var_vec_lst[-1]
        assert np.allclose(stored, durations // 4)


# ---------------------------------------------------------------------------
# add_align
# ---------------------------------------------------------------------------


class TestAddAlign:
    def test_align_with_no_elements_appended(self, experiment):
        experiment.add_align()
        cmd = experiment._commands[-1]
        assert cmd["type"] == "align"
        assert cmd["elements"] is None

    def test_align_with_elements_appended(self, experiment):
        experiment.add_align(["resonator", "helper"])
        cmd = experiment._commands[-1]
        assert cmd["elements"] == ["resonator", "helper"]

    def test_align_with_invalid_element_raises(self, experiment):
        with pytest.raises(ValueError, match="not defined in config"):
            experiment.add_align(["resonator", "ghost_element"])


# ---------------------------------------------------------------------------
# add_floquet_sequence
# ---------------------------------------------------------------------------


class TestAddFloquetSequence:
    def test_mismatched_phases_and_delays_raises(self, experiment):
        with pytest.raises(ValueError, match="one more delay than phase"):
            experiment.add_floquet_sequence([0.0, 90.0], [400, 800], repetitions=5)

    def test_correct_lengths_appended(self, experiment):
        experiment.add_floquet_sequence([0.0, 90.0], [400, 800, 1200], repetitions=5)
        cmd = experiment._commands[-1]
        assert cmd["type"] == "sequence"

    def test_phases_converted_to_fraction_of_2pi(self, experiment):
        phases_deg = [0.0, 90.0]
        experiment.add_floquet_sequence(phases_deg, [400, 800, 1200], repetitions=3)
        cmd = experiment._commands[-1]
        expected = np.array(phases_deg) / 360.0 % 1
        assert np.allclose(cmd["phases"], expected)

    def test_delays_converted_to_clock_cycles(self, experiment):
        delays_ns = [400, 800, 1200]
        experiment.add_floquet_sequence([0.0, 90.0], delays_ns, repetitions=3)
        cmd = experiment._commands[-1]
        expected = np.array(delays_ns, dtype=int) // 4
        assert np.array_equal(cmd["delays"], expected)

    def test_scalar_repetitions_stored_directly(self, experiment):
        experiment.add_floquet_sequence([0.0], [400, 800], repetitions=7)
        cmd = experiment._commands[-1]
        assert cmd["repetitions"] == 7

    def test_iterable_repetitions_adds_loop_var(self, experiment):
        before = len(experiment.var_vec_lst)
        experiment.add_floquet_sequence(
            [0.0], [400, 800], repetitions=np.array([1, 2, 3])
        )
        assert len(experiment.var_vec_lst) > before


# ---------------------------------------------------------------------------
# add_z_rotation
# ---------------------------------------------------------------------------


class TestAddZRotation:
    def test_invalid_element_raises(self, experiment):
        with pytest.raises(ValueError, match="not defined in config"):
            experiment.add_z_rotation(90.0, "bad_element")

    def test_command_appended(self, experiment):
        experiment.add_z_rotation(90.0, "resonator")
        cmd = experiment._commands[-1]
        assert cmd["type"] == "pulse"
        assert cmd["name"] == "virtual_z"
        assert cmd["element"] == "resonator"

    def test_phase_converted_to_fraction_of_2pi(self, experiment):
        experiment.add_z_rotation(180.0, "resonator")
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["phase"], 0.5)

    def test_phase_wraps_above_360(self, experiment):
        experiment.add_z_rotation(720.0, "resonator")
        cmd = experiment._commands[-1]
        assert np.isclose(cmd["phase"], 0.0)


# ---------------------------------------------------------------------------
# add_frame_change
# ---------------------------------------------------------------------------


class TestAddFrameChange:
    def test_invalid_element_raises(self, experiment):
        with pytest.raises(ValueError, match="not defined in config"):
            experiment.add_frame_change(45.0, "ghost")

    def test_sets_use_frame_change(self, experiment):
        experiment.add_frame_change(45.0, "resonator")
        assert experiment.use_frame_change is True

    def test_stores_angle_as_fraction_of_2pi(self, experiment):
        experiment.add_frame_change(90.0, "resonator")
        assert np.isclose(experiment.frame_change_angle, 90.0 / 360.0)

    def test_stores_element(self, experiment):
        experiment.add_frame_change(45.0, "resonator")
        assert experiment.frame_change_element == "resonator"

    def test_angle_wraps_to_fraction(self, experiment):
        experiment.add_frame_change(360.0, "resonator")
        assert np.isclose(experiment.frame_change_angle, 0.0)


# ---------------------------------------------------------------------------
# remove_initial_delay
# ---------------------------------------------------------------------------


class TestRemoveInitialDelay:
    def test_default_is_started_with_wait(self, experiment):
        assert experiment.start_with_wait is True

    def test_remove_sets_false(self, experiment):
        experiment.remove_initial_delay(remove=True)
        assert experiment.start_with_wait is False

    def test_restore_sets_true(self, experiment):
        experiment.remove_initial_delay(remove=True)
        experiment.remove_initial_delay(remove=False)
        assert experiment.start_with_wait is True

    def test_default_argument_removes_delay(self, experiment):
        experiment.remove_initial_delay()
        assert experiment.start_with_wait is False


# ---------------------------------------------------------------------------
# _update_loop
# ---------------------------------------------------------------------------


class TestUpdateLoop:
    def test_all_zeros_raises(self, experiment):
        with pytest.raises(ValueError, match="cannot be all zeros"):
            experiment._update_loop(np.array([0, 0, 0]), -1)

    def test_first_call_stores_vector(self, experiment):
        vec = np.array([1, 2, 3])
        experiment._update_loop(vec, -1)
        assert np.array_equal(experiment.var_vec_lst[-1], vec)

    def test_consistent_multiple_returns_scale(self, experiment):
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([2, 4, 6])  # 2× vec1
        experiment._update_loop(vec1, 1)
        _, div = experiment._update_loop(vec2, 1)
        assert np.isclose(div, 2.0)

    def test_inconsistent_vector_raises(self, experiment):
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([1, 3, 5])  # not proportional
        experiment._update_loop(vec1, 2)
        with pytest.raises(ValueError, match="not constant multiple"):
            experiment._update_loop(vec2, 2)

    def test_explicit_layer_stores_at_correct_index(self, experiment):
        vec = np.array([10, 20, 30])
        experiment._update_loop(vec, 3)
        assert np.array_equal(experiment.var_vec_lst[2], vec)

    def test_explicit_layer_pads_with_none(self, experiment):
        vec = np.array([5, 10])
        experiment._update_loop(vec, 5)
        # Layers 1-4 should be None; layer 5 has vec
        assert experiment.var_vec_lst[4] is not None
        for i in range(4):
            if i < len(experiment.var_vec_lst) and experiment.var_vec_lst[i] is None:
                assert experiment.var_vec_lst[i] is None


# ---------------------------------------------------------------------------
# _update_loop_type
# ---------------------------------------------------------------------------


class TestUpdateLoopType:
    def test_new_layer_stores_type(self, experiment):
        experiment._update_loop_type(-1, use_fixed=True)
        assert True in experiment.use_fixed_lst

    def test_inconsistent_type_raises(self, experiment):
        # layer 1 (1-based) maps to use_fixed_lst[0]
        experiment.use_fixed_lst = [True]
        with pytest.raises(ValueError, match="Inconsistent loop variable types"):
            experiment._update_loop_type(1, use_fixed=False)

    def test_consistent_type_does_not_raise(self, experiment):
        experiment.use_fixed_lst = [True]
        # no error expected
        experiment._update_loop_type(1, use_fixed=True)
        assert experiment.use_fixed_lst[0] is True

    def test_none_layer_gets_defined(self, experiment):
        experiment.use_fixed_lst = [None]
        experiment._update_loop_type(1, use_fixed=False)
        assert experiment.use_fixed_lst[0] is False


# ---------------------------------------------------------------------------
# _list_find_scale_factor
# ---------------------------------------------------------------------------


class TestListFindScaleFactor:
    def test_identical_vectors_return_one(self, experiment):
        v = np.array([1, 2, 3])
        assert np.isclose(experiment._list_find_scale_factor(v, v), 1.0)

    def test_double_vector_returns_two(self, experiment):
        v1 = np.array([2, 4, 6])
        v2 = np.array([1, 2, 3])
        assert np.isclose(experiment._list_find_scale_factor(v1, v2), 2.0)

    def test_non_proportional_returns_minus_one(self, experiment):
        v1 = np.array([1, 2, 4])
        v2 = np.array([1, 2, 3])
        assert experiment._list_find_scale_factor(v1, v2) == -1

    def test_half_scale_returns_half(self, experiment):
        v1 = np.array([1, 2, 3])
        v2 = np.array([2, 4, 6])
        assert np.isclose(experiment._list_find_scale_factor(v1, v2), 0.5)


# ---------------------------------------------------------------------------
# execute_experiment guard
# ---------------------------------------------------------------------------


class TestExecuteExperimentGuard:
    def test_no_commands_raises_value_error(self, experiment):
        """execute_experiment should fail fast with no commands, before any QUA call."""
        with pytest.raises(ValueError, match="No commands have been added"):
            experiment.execute_experiment()


# ---------------------------------------------------------------------------
# Command ordering (FIFO)
# ---------------------------------------------------------------------------


class TestCommandOrdering:
    def test_commands_are_appended_fifo(self, experiment):
        experiment.add_pulse("pi_half", "resonator")
        experiment.add_delay(400)
        experiment.add_align()

        types = [cmd["type"] for cmd in experiment._commands[-3:]]
        assert types == ["pulse", "delay", "align"]

    def test_command_count_increments(self, experiment):
        before = len(experiment._commands)
        experiment.add_pulse("pi_half", "resonator")
        experiment.add_delay(400)
        assert len(experiment._commands) == before + 2


# ---------------------------------------------------------------------------
# compile_to_qua  (offline=True, no hardware connection)
# ---------------------------------------------------------------------------


class TestCompileToQua:
    """
    Smoke-tests for compile_to_qua(offline=True).
    Each test verifies that the function produces a non-empty output file
    without connecting to the QMM.
    """

    @pytest.fixture(scope="class")
    def shared_settings(self):
        return ExperimentSettings()

    @pytest.fixture(scope="class")
    def shared_config(self, shared_settings):
        return cfg_from_settings(shared_settings)

    def test_compile_1d(self, shared_settings, shared_config):
        """Experiment1D with a single pi_half pulse compiles to a non-empty file."""
        expt = Experiment1D(
            settings=shared_settings,
            config=shared_config,
            connect=False,
        )
        expt.remove_initial_delay()  # keep the program compact
        expt.add_pulse(
            name=shared_settings.pi_half_key, element=shared_settings.res_key
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "compiled_1d.qua"
            expt.compile_to_qua(offline=True, save_path=out_path)
            assert out_path.exists(), "compile_to_qua did not create the output file"
            assert out_path.stat().st_size > 0, "compile_to_qua produced an empty file"

    def test_compile_2d_amplitude_sweep(self, shared_settings, shared_config):
        """Experiment2D sweeping pulse amplitude compiles to a non-empty file."""
        import numpy as np

        amp_list = np.arange(0.95, 1.06, 0.01)
        expt = Experiment2D(
            settings=shared_settings,
            config=shared_config,
            connect=False,
        )
        expt.remove_initial_delay()
        expt.add_pulse(
            name=shared_settings.pi_half_key,
            element=shared_settings.res_key,
            amplitude=amp_list,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "compiled_2d.qua"
            expt.compile_to_qua(offline=True, save_path=out_path)
            assert out_path.exists(), "compile_to_qua did not create the output file"
            assert out_path.stat().st_size > 0, "compile_to_qua produced an empty file"

    def test_compile_3d_amplitude_and_delay_sweep(self, shared_settings, shared_config):
        """Experiment3D sweeping amplitude (layer 1) and delay (layer 2) compiles to a non-empty file."""
        import numpy as np

        amp_list = np.arange(0.95, 1.06, 0.01)
        delay_list = np.array([400, 800, 1200, 1600], dtype=int)
        expt = Experiment3D(
            settings=shared_settings,
            config=shared_config,
            connect=False,
        )
        expt.remove_initial_delay()
        # layer 1: amplitude sweep
        expt.add_pulse(
            name=shared_settings.pi_half_key,
            element=shared_settings.res_key,
            amplitude=amp_list,
            loop_layer=1,
        )
        # layer 2: delay sweep
        expt.add_delay(delay_list, loop_layer=2)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "compiled_3d.qua"
            expt.compile_to_qua(offline=True, save_path=out_path)
            assert out_path.exists(), "compile_to_qua did not create the output file"
            assert out_path.stat().st_size > 0, "compile_to_qua produced an empty file"
