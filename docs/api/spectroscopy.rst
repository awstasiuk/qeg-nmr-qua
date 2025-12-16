Spectroscopy Module
===================

The spectroscopy module provides a script for running resonator spectroscopy of the NMR probe.
this script sweeps the frequency of a continuous wave (CW) pulse across a specified range,
measuring the response of the system at each frequency point. This is useful for characterizing
the resonant frequency and quality factor of the NMR probe. However, this experiment requires
simulataneous driving and readout of the resonator, which can potentially damage the hardware
if there is too much amplificiation or power involved. Users should exercise caution and ensure
that the hardware is properly configured and protected before running this experiment.

Currently, this means that the large 300 W power amplifier must be shutoff, then disconnected from
the OPX-1000. Direct output from the OPX LF-FEM should be run throught the amplifier bypass cable,
which then must be connected to the circulator input port. Future hardware implementations will
hopefully include electromechanical switches in order to isolate the amplifier during this experiment.

This function is called wobb because Bruker called it wobb and it sounds cute.

WOBB (Wobble)
-------------

.. automodule:: qeg_nmr_qua.spectroscopy.wobb
   :members:
   :undoc-members:
   :show-inheritance:
