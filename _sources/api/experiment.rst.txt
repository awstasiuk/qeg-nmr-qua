Experiment Module
=================

The experiment module provides a hierarchy of classes for building, validating, and
executing NMR pulse sequences on the OPX-1000.  The base class
:class:`~qeg_nmr_qua.experiment.experiment.Experiment` holds the command queue,
configuration, and shared infrastructure.  The concrete subclasses
:class:`~qeg_nmr_qua.experiment.experiment_1d.Experiment1D`,
:class:`~qeg_nmr_qua.experiment.experiment_2d.Experiment2D`, and
:class:`~qeg_nmr_qua.experiment.experiment_3d.Experiment3D`
implement the loop structure and data-processing logic appropriate to each
experiment dimensionality.


Designing Experiments
---------------------

The three concrete subclasses differ only in how many swept parameters they support:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Class
     - Swept parameters
     - Typical use cases
   * - ``Experiment1D``
     - 0
     - FID, single-pulse readout
   * - ``Experiment2D``
     - 1
     - T1, T2, pulse calibration, Floquet correlation measurements
   * - ``Experiment3D``
     - 2
     - Joint relaxation / amplitude scans, Multiple Quantum Coherence (MQC) experiments


Adding commands
~~~~~~~~~~~~~~~

Pulse sequences are built by appending commands before execution.
All commands accept either scalar or iterable (NumPy array) arguments
for the swept dimension.

.. code-block:: python

   expt.add_pulse(name, element, phase=0.0, amplitude=1.0, length=None)
   expt.add_delay(duration)
   expt.add_align(elements=None)
   expt.add_floquet_sequence(phases, delays, repetitions)
   expt.add_z_rotation(angle, element)    # virtual-Z gate (frame rotation)
   expt.add_frame_change(angle, element)  # per-pulse frame correction

Scalar arguments produce a fixed value in the compiled QUA program.
Passing a NumPy array registers a **loop variable**; the array becomes
the sweep vector iterated over in the QUA ``for_`` loop.


Loop layers and QUA variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each swept dimension corresponds to one **loop layer**.  The
``loop_layer`` keyword selects which QUA loop variable a command's
array is bound to.  The indexing is **1-based**:

.. list-table::
   :header-rows: 1
   :widths: 15 25 25 35

   * - ``loop_layer``
     - Internal slot ``var_vec_lst[...]``
     - QUA variable name
     - Sweep speed
   * - ``1``
     - ``var_vec_lst[0]``
     - ``var_outer`` (3D) / ``var`` (2D)
     - Outermost swept loop — *slowest* changing
   * - ``2``
     - ``var_vec_lst[1]``
     - ``var_inner`` (3D only)
     - Inner swept loop — *fastest* changing

The default value ``loop_layer=-1`` instructs the class to **automatically
assign** the variable to the first unfilled slot.  Explicit values are
strongly preferred in 3D experiments to avoid accidental axis transposition.


Designing a 2D experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Assign a NumPy array to any ``add_*`` argument.  All arrays across all
commands in the experiment must be identical or a **constant scalar multiple**
of each other — they all map to the *same* QUA variable.

.. code-block:: python

   import numpy as np, qeg_nmr_qua as qnmr
   from qualang_tools.units import unit

   u = unit(coerce_to_integer=True)
   amp_list = np.arange(0.93, 1.05, 0.01)

   expt = qnmr.Experiment2D(settings=settings, config=cfg)
   expt.add_pulse(
       name=settings.pi_half_key,
       element=settings.res_key,
       amplitude=amp_list,       # marks amp_list as layer-1 sweep
   )
   # A second pulse whose amplitude is 2× amp_list is still consistent:
   expt.add_pulse(
       name=settings.pi_half_key,
       element=settings.res_key,
       amplitude=2 * amp_list,   # scalar-multiple of existing vector — OK
   )
   expt.update_sweep_axis(amp_list * settings.pulse_amplitude)
   expt.update_sweep_label("Pulse Amplitude (Vpp)")
   expt.execute_experiment()


Designing a 3D experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~

Two independent arrays must be provided, one per loop layer.
The data shape returned after ``execute_experiment`` is
**``(n_outer, n_inner, n_time)``** — axes ordered from slowest to fastest varying,
followed by the readout time axis.

Rule summary
^^^^^^^^^^^^

* ``loop_layer=1`` → stored in ``var_vec_lst[0]`` → compiled into the **outer**
  (slow) QUA loop as ``var_outer``.
* ``loop_layer=2`` → stored in ``var_vec_lst[1]`` → compiled into the **inner**
  (fast) QUA loop as ``var_inner``.
* Multiple commands may share the same ``loop_layer`` provided their arrays
  are constant multiples of each other.
* Mixing integer and fixed-point types **within the same layer** raises a
  ``ValueError`` at build time.

.. code-block:: python

   import numpy as np, qeg_nmr_qua as qnmr
   from qualang_tools.units import unit

   u = unit(coerce_to_integer=True)

   # Define the two sweep axes explicitly:
   delay_list = np.array([1, 2, 4, 8, 16, 32]) * u.us   # outer (slow)
   amp_list   = np.arange(0.95, 1.06, 0.01)             # inner (fast)

   expt = qnmr.Experiment3D(settings=settings, config=cfg)

   # layer=1 → outer loop (slow sweep, var_outer in QUA)
   expt.add_delay(delay_list, loop_layer=1)

   # layer=2 → inner loop (fast sweep, var_inner in QUA)
   expt.add_pulse(
       name=settings.pi_half_key,
       element=settings.res_key,
       amplitude=amp_list,
       loop_layer=2,
   )

   expt.update_sweep_axis_outer(delay_list / u.us)
   expt.update_sweep_label_outer("Delay (µs)")
   expt.update_sweep_axis_inner(amp_list * settings.pulse_amplitude)
   expt.update_sweep_label_inner("Pulse Amplitude (Vpp)")

   expt.execute_experiment()

   # I_data shape: (6, 11, n_time)
   I_data = expt.save_data_dict["I_data"]


.. warning::

   **Incorrect ``loop_layer`` is a silent data-ordering bug.**  The program
   will compile and run without error, but the outer and inner axes of the
   data array will be swapped.  To verify loop assignments before running
   on hardware, use :meth:`~qeg_nmr_qua.experiment.experiment.Experiment.compile_to_qua`
   with ``offline=True`` and inspect the generated ``for_`` nesting in the
   output file.


Variable types: integer vs. fixed-point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QUA distinguishes between integer (``int``) and fixed-point (``fixed``) variables.
The type is inferred from the swept parameter:

* **Amplitudes and phases** → ``fixed`` (fractional values).
* **Durations** (delays, pulse lengths) → ``int`` (clock cycles, always integer).

The class records the inferred type in ``use_fixed_lst`` and declares the
corresponding QUA variable type when the program is compiled.  You cannot mix
integer and fixed-point arrays on the same loop layer.


Inspecting the compiled program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.compile_to_qua` generates
the full QUA script as a plain-text file without connecting to hardware:

.. code-block:: python

   expt.compile_to_qua(offline=True, save_path=Path("my_experiment.qua"))

This is the recommended first step for any new 3D experiment — confirm that
``var_outer`` and ``var_inner`` appear in the expected ``for_`` loop positions.


Subclassing the base class
--------------------------

Advanced users can subclass :class:`~qeg_nmr_qua.experiment.experiment.Experiment`
directly to implement custom loop structures or non-standard readout schemes.  Three
methods must be overridden:

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.validate_experiment`
   Called before the QUA program is compiled.  Raise ``ValueError`` for any
   inconsistency that would cause a QUA runtime error (e.g. missing loop vectors,
   incompatible lengths).  This catches user errors *before* they propagate into
   hard-to-read QUA tracebacks.

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.create_experiment`
   Builds and returns the QUA ``program()`` object.  Call
   :meth:`~qeg_nmr_qua.experiment.experiment.Experiment.translate_command` for
   each item in ``self._commands`` to emit the pulse/delay/align QUA instructions.
   **All timings must be expressed in clock cycles (divide nanoseconds by 4).**
   Data streams must be buffered consistently with the expected shape consumed in
   ``data_processing``.

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.data_processing`
   Called after the job is launched.  Fetch data via ``qualang_tools.results.fetching_tool``,
   convert demodulated values to volts, and populate ``self.save_data_dict``.


Safety macros
~~~~~~~~~~~~~

The :mod:`~qeg_nmr_qua.experiment.macros` module provides three macros that must be
called in the correct order to protect the hardware:

.. code-block:: text

   drive_mode(switch, amplifier)    # open switch, unblank amplifier — before pulse sequence
   safe_mode(switch, amplifier)     # blank amplifier, open switch   — after pulse sequence
   readout_mode(switch, amplifier)  # close switch, blank amplifier  — during readout

All three insert ``align()`` calls and explicit wait times (``RX_SWITCH_DELAY``,
``AMPLIFIER_BLANKING_TIME``) to ensure hardware state transitions complete before
the next operation.


Base Experiment
---------------

.. automodule:: qeg_nmr_qua.experiment.experiment
   :members:
   :undoc-members:
   :show-inheritance:

1D Experiments
--------------

.. automodule:: qeg_nmr_qua.experiment.experiment_1d
   :members:
   :undoc-members:
   :show-inheritance:

2D Experiments
--------------

.. automodule:: qeg_nmr_qua.experiment.experiment_2d
   :members:
   :undoc-members:
   :show-inheritance:

3D Experiments
--------------

.. automodule:: qeg_nmr_qua.experiment.experiment_3d
   :members:
   :undoc-members:
   :show-inheritance:

Experiment Macros
-----------------

.. automodule:: qeg_nmr_qua.experiment.macros
   :members:
   :undoc-members:
   :show-inheritance:
