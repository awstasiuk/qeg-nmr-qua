"""This file is for git testing purposes, for Mason to become familiar with branches, push & pull requests.
It was last updated 1/22/26 10:25am

git checkout mason/gitsandbox
git commit -m "message"
git push origin mason/gitsandbox

If its been a while since the last calibration:
Step 0: Calibrate the "wobb" (wobble?) (a.k.a. resonator spectroscopy)
	a. Turn off the big amplifier.
	b. Unplug the QM Xoutput from the amplifier's Xinput. Unplug the amplifier from the circulator circuit 
	c. Plug the QM Xoutput into the circulator circuit.
	d. Danger Zone: resspec.py & wobb.py. Only use if big amplifier is off & disconnected!
	e. Tune the two knobs under the NMR: one is frequency tuning, the other is shape/amplitude tuning (this one is finnicky) (aim for < 0.5e-5 loss)
	f. End the Danger Zone script.
	g. Return the wires to the original positions, then turn the big amp back on

Step 1: Calibrate the offset-freq & phase
As time goes on, the magnet demagnetizes slowly, leading to a small detuning (right now ~5000Hz) of the frequency from our expected center (282.1901 MHz). We also must shift phase (right now, ~245° but varies).
	a. Zero-go: zg.py. Will spit out the I and Q vs t curves.
	b. Script uses simple trigonometry to tune the phase.
	c. The Q and auto-correlation will tell you how you must tune the offset-freq. If the Q concavity is positive, offset-freq is too high. If Q concavity is negative, offset-freq is too low.
	d. Repeat steps a-c and gradually adjust until Q approaches noise. Alternatively, autocal.py is meant to do this automatically

Step 2: Calibrate the pulse amplitude
Each pulse (e.g. pi/2 square pulse, gaussian, etc.) needs to have its amplitude tuned in order to maximize I.
	a. pulcal_1x.py, performs an amplitude sweep. It takes the pulse_amplitude from the config and scales it by the amp_list. 
		e.g. pulse_amplitude=0.441 Vpp and amp_list = np.arange(.93,1.05,.01) sweeps from 93% (0.410Vpp) to 105% (0.464Vpp) in increments of 1%.
	It then runs the pulse once, and then runs it 4*n_wraps times again (for a pi/2 pulse, 4 pulses is approximately identity and "wraps" back around). Then it measures the amplitude of I.
	b. Fits the results to a parabola to find which pulse amplitude leads to the best I amplitude. We can adjust n_wraps to test further.

Step 3: Calibrate the Over Rotation Error
Our pulses are not perfectly accurate: e.g. a square pulse has a leading and trailing edge. ∫d?(φ_'lead' - φ_'trail')≈10°
This leads to a Y component from our pulse, an "over rotation" which must be corrected with a frame change.
Stasiuk, Andrew, et al. "Frame change technique for phase transient cancellation." Journal of Magnetic Resonance 362 (2024): 107688.
	a. Overrotation calibration: overrotcal_xy.py. This script will supposedly correct for the frame change. For the most part, any overrotation <6° is not a big deal.

"""