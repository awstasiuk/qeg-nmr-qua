import json
from pathlib import Path
from matplotlib import cm
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D

fit = True
remove_echo_decay = True # For observing operator spreading |Cₘ(t)|² / Σₘ|Cₘ(t)|²

if fit:
    # Load JSON file
    data_path = Path.home() / "Dropbox/QEG/NMR/RawData/mqc_expt/experiment_0007/data.json"
    with open(data_path, "r") as f:
        data_dict = json.load(f)

    re = np.array(data_dict["I_data"]) * 1e6
    periods = np.array(data_dict["sweep_axis_outer"])
    rotation_deg = np.array(data_dict["sweep_axis_inner"])
    re = re[:, :, 0]  # Plot first point of FID for each period & rotation
    n_periods, n_phi = re.shape

    # normalize to φ=0 to remove echo decay envelope and observe operator spreading
    if remove_echo_decay: signal = re / re[:, 0][:, np.newaxis]
    # preserve echo decay envelope, observe MQC intensities more quantitatively
    else: signal = re / re[0,0] 

    # FFT over φ to extract MQC intensities
    rotation_rad = np.deg2rad(rotation_deg)
    dphi = np.mean(np.diff(rotation_rad))
    mqc = np.fft.fft(signal, axis=1) / n_phi
    mqc = np.fft.fftshift(mqc, axes=1)
    mqc_intensity = np.abs(mqc)
    coherence_orders = np.fft.fftshift(np.fft.fftfreq(n_phi, d=dphi/(2*np.pi))) # Frequency axis (coherence order)

    # 3D Plot
    fig = plt.figure()
    ax2 = fig.add_subplot(1, 1, 1, projection='3d')

    # render MQC intensity of each order back to front
    sort_idx = np.argsort(coherence_orders)[::-1]
    for j in sort_idx:
        threshold = 0.05 # gray out low intensity coherences
        if np.average(mqc_intensity[:, j]) < threshold: color = 'darkgray'
        else: color = None

        ax2.plot(periods, np.full_like(periods, coherence_orders[j]), 
                mqc_intensity[:, j], color=color)

    ax2.set_xlabel("Floquet Periods"); ax2.set_xlim(0, periods.max())
    ax2.set_ylabel("Coherence Order"); ax2.set_yticks(np.arange(coherence_orders.min(), coherence_orders.max(), step=2))
    ax2.set_zlabel("MQC Intensity"); ax2.set_zlim(0, mqc_intensity.max())
    
    plt.title("MQC Intensities" + (" (Normalized Echo Decay)" if remove_echo_decay else ""))
    plt.tight_layout()
    plt.show()