Quick Start Guide
=================

This guide will help you get started with qeg-nmr-qua.

Basic Configuration
-------------------

Import the necessary modules:

.. code-block:: python

   from qeg_nmr_qua import OPXConfig, ExperimentSettings, cfg_from_settings

Create an experiment configuration:

.. code-block:: python

   # Define your experiment settings
   settings = ExperimentSettings(
       # Add your settings here
   )
   
   # Generate OPX configuration from settings
   config = cfg_from_settings(settings)

Running a 1D Experiment
-----------------------

.. code-block:: python

   from qeg_nmr_qua import Experiment1D
   
   # Create and run a 1D experiment
   exp = Experiment1D(config)
   # Run your experiment
   
Working with Data
-----------------

.. code-block:: python

   from qeg_nmr_qua.analysis import DataSaver
   
   # Save experimental data
   saver = DataSaver()
   # Use the saver to store your results

Next Steps
----------

* Check out the :doc:`api/index` for detailed API documentation
* See the ``examples/`` directory for more complete examples
* Read about specific modules in the API reference
