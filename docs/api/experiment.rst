Experiment Module
=================

The experiment module provides classes for running a variety of standard NMR experiments. The base class,
:class:`~qeg_nmr_qua.experiment.experiment.Experiment`, contains common functionality for all experiments, while the :class:`~qeg_nmr_qua.experiment.experiment_1d.Experiment1D` and :class:`~qeg_nmr_qua.experiment.experiment_2d.Experiment2D`
classes implement specific logic for one-dimensional and two-dimensional experiments, respectively. Each base class
needs to implement three main methods: :meth:`~qeg_nmr_qua.experiment.experiment.Experiment.validate_experiment`, :meth:`~qeg_nmr_qua.experiment.experiment.Experiment.create_experiment`, and :meth:`~qeg_nmr_qua.experiment.experiment.Experiment.live_data_processing`.

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.validate_experiment` checks that the provided parameters are valid for the specific experiment type, and is useful
for catching user errors before running the experiment. Generally, this should catch what would otherwise be runtime
errors in the QUA program.

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.create_experiment` builds the QUA program for the specific experiment, using the provided parameters and
configuration. This method should define and return the QUA program. Users should be especially careful to ensure that
within the QUA program, all variables will be QUA variables, and so are subject to QUA's restrictions. Mid-experiment
computations (such as division) can over 20 clock cycles, and lead to unexpected behavior if not handled properly. Further,
QUA functions usually expect timings in terms of clock cycles (4 ns), so users should convert from seconds to clock cycles
as needed, which is usually handled in the :class:`~qeg_nmr_qua.experiment.experiment.Experiment` base class. The extracted data must be buffered in accordance to
the expected :meth:`~qeg_nmr_qua.experiment.experiment.Experiment.live_data_processing` behavior. Finally, the QUA program should ensure judicious use of the safety macros
provided in :mod:`~qeg_nmr_qua.experiment.macros` to prevent hardware damage.

:meth:`~qeg_nmr_qua.experiment.experiment.Experiment.live_data_processing` defines how to process and visualize the data as it is acquired. This method is called
periodically during the experiment, and should handle fetching the data from the OPX, processing it (e.g., averaging,
Fourier transforming), and updating any plots or visualizations. Data the needs to be saved should be added to the class' 
:attr:`~qeg_nmr_qua.experiment.experiment.Experiment.save_data_dict` attribute, which is saved to file at the end of the experiment.

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

Experiment Macros
-----------------

.. automodule:: qeg_nmr_qua.experiment.macros
   :members:
   :undoc-members:
   :show-inheritance:
