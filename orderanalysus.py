import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft

# Example signals
mic_signal = ...   # microphone signal [Pa]
rpm_signal = ...   # rpm signal [RPM]
time = ...         # time vector [s]

# Convert RPM to Hz
rot_freq = rpm_signal / 60.0  # shaft frequency [Hz]

# STFT of microphone
f, t_stft, Zxx = stft(mic_signal, fs=48000, nperseg=2048, noverlap=1024)

# Interpolate rot_freq to STFT time axis
rot_freq_interp = np.interp(t_stft, time, rot_freq)

# Convert frequency to orders
orders = np.zeros_like(f[:, None] / rot_freq_interp[None, :])
for i in range(len(t_stft)):
    orders[:, i] = f / rot_freq_interp[i]

# Amplitude in dB
amplitude_db = 20*np.log10(np.abs(Zxx) + 1e-12)

# Plot Order Map
plt.figure(figsize=(10,6))
plt.pcolormesh(t_stft, orders, amplitude_db, shading='auto', cmap='jet')
plt.colorbar(label='Amplitude [dB]')
plt.ylabel('Order')
plt.xlabel('Time [s]')
plt.title('Order Spectrum Map')
plt.ylim(0, 20)  # show first 20 orders
plt.show()
