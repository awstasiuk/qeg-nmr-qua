Configuration Module
====================

The configuration module provides classes and utilities for managing OPX-1000 configurations. The :class:`~qeg_nmr_qua.config.settings.Settings`
class contains high-level parameters for nuclear spin control, while the other classes define specific configuration
elements such as chasis, controller, element, pulse, waveform, and integration weights. Unless modifying the 
hardware configureation, users will primarily interact with the :class:`~qeg_nmr_qua.config.settings.Settings` class and the configuration generator function,
:func:`~qeg_nmr_qua.config.config_from_settings.config_from_settings`.

Settings
--------

.. automodule:: qeg_nmr_qua.config.settings
   :members:
   :undoc-members:
   :show-inheritance:

Configuration from Settings
---------------------------

.. automodule:: qeg_nmr_qua.config.config_from_settings
   :members:
   :undoc-members:
   :show-inheritance:

Chassis Configuration
---------------------

.. automodule:: qeg_nmr_qua.config.config
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

Controller Configuration
-------------------------

.. automodule:: qeg_nmr_qua.config.controller
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

Element Configuration
----------------------

.. automodule:: qeg_nmr_qua.config.element
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

Pulse Configuration
-------------------

.. automodule:: qeg_nmr_qua.config.pulse
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

Waveform Configuration
----------------------

.. automodule:: qeg_nmr_qua.config.waveform
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:

Integration Weights
-------------------

.. automodule:: qeg_nmr_qua.config.integration
   :members:
   :undoc-members:
   :show-inheritance:
   :no-index:
