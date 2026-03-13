Quick Start Guide
=================

This guide walks through the full workflow for designing and running NMR experiments
with **qeg-nmr-qua**, from basic configuration through to 3D parameter sweeps.

.. contents:: On this page
   :local:
   :depth: 2


Setup and Configuration
-----------------------

All experiments start with an :class:`~qeg_nmr_qua.config.settings.ExperimentSettings`
object. This is the single source of truth for pulse, frequency, and readout parameters.
The OPX hardware configuration is then generated automatically from those settings:

.. code-block:: python

   from qualang_tools.units import unit
   from pathlib import Path
   import qeg_nmr_qua as qnmr

   u = unit(coerce_to_integer=True)

   settings = qnmr.ExperimentSettings(
       n_avg=4,
       pulse_length=1.1 * u.us,
       pulse_amplitude=0.422,       # 0.5 * Vpp
       rotation_angle=248.0,        # degrees
       thermal_reset=4 * u.s,
       center_freq=282.1901 * u.MHz,
       offset_freq=4500 * u.Hz,
       readout_delay=20 * u.us,
       dwell_time=4 * u.us,
       readout_start=0 * u.us,
       readout_end=256 * u.us,
       save_dir=Path("results"),
   )

   cfg = qnmr.cfg_from_settings(settings)

Settings are validated on update; call ``settings.validate()`` directly if you change
values manually. All time values are in **nanoseconds** internally; use the ``unit``
helper to express them in physical units.


Building a Pulse Sequence
--------------------------

Experiments are constructed by appending **commands** to an experiment object.  Six
command types are available:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Effect
   * - ``add_pulse(...)``
     - RF pulse with optional phase, amplitude, or length
   * - ``add_delay(...)``
     - Free-evolution delay
   * - ``add_align(...)``
     - Align one or more elements in time
   * - ``add_floquet_sequence(...)``
     - Repeating multi-pulse / delay block
   * - ``add_z_rotation(...)``
     - Frame change (virtual Z rotation) on one or more elements
   * - ``add_measurement(...)``
     - Acquisition command for phase control and phase cycling while averaging

Commands are translated into QUA code in FIFO order when
:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.create_experiment` is called. Every 
experiment must end with a measurement command to be valid, and must not contain more
than one measurement command per readout scan.


1D Experiment — Free Induction Decay
-------------------------------------

:class:`~qeg_nmr_qua.experiment.experiment_1d.Experiment1D` measures the FID following
a single π/2 pulse.  No swept parameter is needed; every command must use
scalar (non-iterable) arguments.

.. code-block:: python

   expt = qnmr.Experiment1D(settings=settings, config=cfg)

   # A single π/2 pulse about y on the resonator element
   expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, phase=90)

   # measure the FID along the x axis (phase=0) for maximal signal in the I channel
   expt.add_measurement(phase=0, phase_cycle=False)

   expt.execute_experiment()

   # Inspect data
   import numpy as np
   I = np.array(expt.save_data_dict["I_data"])
   Q = np.array(expt.save_data_dict["Q_data"])

.. note::

   If you pass an iterable (e.g. a NumPy array) to any argument of a command in a
   ``Experiment1D``, ``validate_experiment()`` will raise a ``ValueError`` before the
   QUA program is compiled.


2D Experiment — Sweeping One Parameter
---------------------------------------

:class:`~qeg_nmr_qua.experiment.experiment_2d.Experiment2D` loops over a single
**swept variable vector**.  Pass a NumPy array to one argument of *any* command and
the class records it as the sweep axis.

The **loop nesting order** is: **averages (outer) → swept variable → readout scan (inner-most)**.
This means the sweep is traversed in full before the next average begins, which helps
mitigate slow parameter drifts.


Example: pulse-amplitude calibration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import numpy as np
   import qeg_nmr_qua as qnmr

   amp_list = np.arange(0.93, 1.05, 0.01)   # amplitude rescaling factors

   expt = qnmr.Experiment2D(settings=settings, config=cfg)

   # Sweep the amplitude — every add_pulse call with the same array
   # is automatically recognised as the same loop variable.
   expt.add_pulse(
       name=settings.pi_half_key,
       element=settings.res_key,
       amplitude=amp_list,
       phase=[90,270],
       phase_cycle=True,
   )

   # Add a measurement with phase cycling to see the effect of the pulse amplitude on the FID
   # while reducing systematic errors. Phase cycling accumulates during the averaging loop, and does
   # not affect the loop variable assignment since it is a separate iterable argument.
   expt.add_measurement(phase=[0, 180], phase_cycle=True)

   # Optionally convert the raw rescaling factor to physical units for plots
   expt.update_sweep_axis(amp_list * settings.pulse_amplitude)  # volts
   expt.update_sweep_label("Pulse Amplitude (Vpp)")

   expt.execute_experiment()

   I_data = expt.save_data_dict["I_data"]   # shape (n_sweep, n_time)


Example: Floquet (Hamiltonian-engineering) sweep
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from qualang_tools.units import unit
   u = unit(coerce_to_integer=True)

   t0   = 5 * u.us
   p1   = settings.pulse_length
   thlf = (t0 - p1) // 2
   t1   = t0 - p1
   t2   = 2 * t1 - p1

   pine8_phases = np.array([0, 0, 0, 0, 180, 180, 180, 180])
   pine8_delays = np.array([thlf, t2, t1, t2, t1, t2, t1, t2, thlf])

   period_list = np.arange(0, 25, 1)         # 0 to 24 Floquet periods

   expt = qnmr.Experiment2D(settings=settings, config=cfg)
   expt.add_frame_change(angle=5.50, element=settings.res_key)
   expt.add_floquet_sequence(
       phases=pine8_phases,
       delays=pine8_delays,
       repetitions=period_list,           # iterable → sweep variable
   )
   expt.add_delay(1 * u.ms)              # T1 filter
   expt.add_pulse(name=settings.pi_half_key, element=settings.res_key, phase=[90, 270], phase_cycle=True)

   expt.add_measurement(phase=[0,180], phase_cycle=True)

   expt.update_sweep_axis(period_list)
   expt.update_sweep_label("Pine-8 Periods")
   expt.execute_experiment()


Consistency rule
~~~~~~~~~~~~~~~~~

All iterable arguments across *all* commands in a ``Experiment2D`` must either be
the **same** array or a **constant multiple** of that array.  Mixing incompatible
vectors raises a ``ValueError``.


3D Experiment — Sweeping Two Parameters
-----------------------------------------

:class:`~qeg_nmr_qua.experiment.experiment_3d.Experiment3D` extends the 2D framework
to **two independent swept variables**.  Understanding the loop layer convention is
essential to getting the correct data shape and avoiding subtle bugs.

The **loop nesting order** is: 
**averages (outer) → swept variable 1 (slow) → swept variable 2 (fast) → readout scan (inner-most)**.
This means that current `live_plot` implementations will take a long time to update if the product
of the two sweep dimensions is large, since the full inner loop must be traversed before the next point in the
 outer loop is reached. 


Loop layer convention
~~~~~~~~~~~~~~~~~~~~~

The ``loop_layer`` keyword argument is **1-based** and controls which QUA loop variable
a command's iterable is bound to.

.. list-table::
   :header-rows: 1
   :widths: 15 20 20 45

   * - ``loop_layer``
     - ``var_vec_lst`` slot
     - QUA variable
     - Role in the loop nest
   * - ``1``
     - ``var_vec_lst[0]``
     - ``var_outer``
     - **Outer** (slow) sweep — changes less frequently
   * - ``2``
     - ``var_vec_lst[1]``
     - ``var_inner``
     - **Inner** (fast) sweep — changes most frequently

The full loop nest executes as:

.. code-block:: text

   for average in range(n_avg):              # outermost
       for value_outer in var_vec_lst[0]:    # layer 1 — slow sweep
           for value_inner in var_vec_lst[1]: # layer 2 — fast sweep
               <pulse sequence>
               <readout>

The resulting data arrays have shape
``(n_outer, n_inner, n_time)`` after averaging.


Example: joint amplitude + delay sweep
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import numpy as np
   import qeg_nmr_qua as qnmr
   from qualang_tools.units import unit

   u = unit(coerce_to_integer=True)

   # Layer 1 (outer / slow): vary the delay between pulses
   # Layer 2 (inner / fast): vary the pulse amplitude

   delay_list = np.array([1, 2, 4, 8, 16, 32]) * u.us   # 6 outer points
   amp_list   = np.arange(0.95, 1.06, 0.01)             # 11 inner points

   expt = qnmr.Experiment3D(settings=settings, config=cfg)

   # --- Pulse 1: amplitude is swept (inner loop, layer 2) ---
   expt.add_pulse(
       name=settings.pi_half_key,
       element=settings.res_key,
       amplitude=amp_list,
       loop_layer=2,               # <-- inner / fast sweep
   )

   # --- Delay: duration is swept (outer loop, layer 1) ---
   expt.add_delay(delay_list, loop_layer=1)   # <-- outer / slow sweep

   # --- Pulse 2: same amplitude sweep must be consistent with layer 2 ---
   expt.add_pulse(
       name=settings.pi_half_key,
       element=settings.res_key,
       amplitude=amp_list,
       loop_layer=2,
   )

   expt.add_measurement(phase=90, phase_cycle=False)

   expt.update_sweep_axis_outer(delay_list / u.us)
   expt.update_sweep_label_outer("Delay (µs)")
   expt.update_sweep_axis_inner(amp_list * settings.pulse_amplitude)
   expt.update_sweep_label_inner("Pulse Amplitude (Vpp)")

   expt.execute_experiment()

   # Data shape: (n_outer=6, n_inner=11, n_time)
   I_data = expt.save_data_dict["I_data"]


.. warning::

   **Assigning the wrong loop layer is a silent data-ordering error.**
   If you intend a variable to be the slow sweep but assign
   ``loop_layer=2`` instead of ``loop_layer=1``, the QUA program will
   compile and run without error but the data axes will be transposed.
   Always match ``loop_layer=1`` to ``var_vec_lst[0]`` (outer loop) and
   ``loop_layer=2`` to ``var_vec_lst[1]`` (inner loop).


Omitting ``loop_layer`` in a 3D experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When ``loop_layer`` is not specified (default ``-1``), the experiment
automatically assigns the variable to the **first unfilled slot**:

* The first iterable encountered fills layer 1 (outer).
* The second *distinct* iterable encountered fills layer 2 (inner).
* A second call using an array that is a scalar multiple of an existing
  layer's vector is merged into that same layer.

This auto-assignment is convenient for simple cases but **explicit
``loop_layer`` values are strongly recommended** for 3D experiments to
prevent accidental ordering mistakes.


Checking the generated QUA program
------------------------------------

Before running on hardware, you can inspect the compiled QUA program offline:

.. code-block:: python

   from pathlib import Path

   expt.compile_to_qua(
       offline=True,
       save_path=Path("compiled_experiment.qua"),
   )

This writes a plain-text file containing the full QUA script and does not
require a hardware connection.  Use it to verify pulse ordering, timing, and
that sweep variables appear in the expected loop positions.


Saving Data
-----------

Data is persisted automatically at the end of
:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.execute_experiment` via
:class:`~qeg_nmr_qua.analysis.data_saver.DataSaver`.  You can also trigger a manual
save at any point:

.. code-block:: python

   expt.save_data(experiment_prefix="pulse_cal")

This creates a folder ``pulse_cal_0001/`` (auto-incremented) containing:

* ``config.json``   — OPX hardware configuration
* ``settings.json`` — Experiment settings
* ``commands.json`` — Serialised command list
* ``data.json``      — Averaged I/Q data and metadata


Next Steps
----------

* :doc:`api/experiment` — Complete API reference and design notes for subclass extensions
* :doc:`api/config` — Configuration and settings API
