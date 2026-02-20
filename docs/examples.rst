Examples
========

These examples will introduce you to experiments and calibration with the qeg-nmr-qua package.

Resonator Spectroscopy
----------------------

Step 0: Calibrate the "wobb" (wobble) 

If its been a while since the last calibration, we must calibrate the wobb to maximize the signal from the resonator (a.k.a. resonator spectroscopy. See :doc:`api/Spectroscopy` for more details). Resonator spectroscopy. 
Here, we measure the response of a resonator over a range of frequencies using a continuous wave excitation (wobbler). The response is measured in terms of the I and Q quadratures of the transmitted signal.
You must be careful with this process, as the big amplifier can be damaged if not properly disconnected. 

a. Turn off the big amplifier.
b. Unplug the QM Xoutput from the amplifier's Xinput. Unplug the amplifier from the circulator circuit 
c. Plug the QM Xoutput into the circulator circuit.
d. Danger Zone: resspec.py & wobb.py. Only use if big amplifier is off & disconnected!
e. Tune the two knobs under the NMR: one is frequency tuning, the other is shape/amplitude tuning (this one is finnicky) (aim for < 0.5e-5 loss)
f. End the Danger Zone script.
g. Return the wires to the original positions, then turn the big amp back on

Offset & Phase Calibrate (Zero-go)
----------------------------------

Step 1: Calibrate the offset-freq & phase.

As time goes on, the magnet demagnetizes slowly, leading to a small detuning (~1000s of Hz/week) of the frequency from our expected center (282.1901 MHz), and our phase drifts. 
We can accont for this detuning and phase drift by performing a simple free induction decay (FID) experiment.
This reproduces the "zero-go" function often used in Brucker systems.

a. Zero-go: zg.py. Will spit out the I and Q vs t curves.
b. Script uses simple trigonometry to tune the phase.
c. The Q and auto-correlation will tell you how you must tune the offset-freq. 
* If the Q concavity is positive, offset-freq is too high. 
* If Q concavity is negative, offset-freq is too low.
d. Repeat steps a-c and gradually adjust until Q approaches noise. Alternatively, autocal.py is meant to do this automatically

Pulse Amplitude Calibration
---------------------------

Step 2: Calibrate the pulse amplitude.

Each pulse (e.g. pi/2 square pulse, gaussian, etc.) needs to have its amplitude/timing tuned in order to maximize I over several wraps.
This example shows how to run a 2D pulse calibration experiment; it applies a series of pulses with varying amplitudes to the nuclear spin system and measures the resulting FID signals.

a. pulcal_1x.py, performs an amplitude sweep. It takes the pulse_amplitude from the config and scales it by the amp_list. 
* e.g. pulse_amplitude=0.441 Vpp and amp_list = np.arange(.93,1.05,.01) sweeps from 93% (0.410Vpp) to 105% (0.464Vpp) in increments of 1%.
* It then runs the pulse once, and then runs it 4*n_wraps times again (for a pi/2 pulse, 4 pulses is approximately identity and "wraps" back around). Then it measures the amplitude of I.
b. Fits the results to a parabola to find which pulse amplitude leads to the best I amplitude. We can adjust n_wraps to test further.

Overrotaion Calibration
-----------------------

Step 3: Calibrate the Over Rotation Error

Our pulses are not perfectly accurate: e.g. a square pulse has a different leading and trailing edge. ∫d?(φ_'lead' - φ_'trail')≈10°
This leads to a Y component from our pulse, an "over rotation" which must be corrected with a frame change.
Stasiuk, Andrew, et al. "Frame change technique for phase transient cancellation." Journal of Magnetic Resonance 362 (2024): 107688.

a. Overrotation calibration: overrotcal_xy.py. This script will determine the necessary frame change


Next Steps
----------

* Check out the :doc:`api/index` for detailed API documentation
* Read about specific modules in the API reference