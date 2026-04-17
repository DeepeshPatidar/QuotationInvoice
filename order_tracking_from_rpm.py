"""
order_tracking_from_rpm.py

Computed-order (angular) resampling using an RPM channel (Keyence optical RPM).
Follows the workflow in MathWorks "Vibration analysis of rotating machinery".
*** MODIFIED TO USE RAW SIGNAL AND SAVE FIGURES TO PDF/PNG. ***

Requirements:
  - Python 3.8+
  - numpy, scipy, pandas, matplotlib
  - matplotlib.backends.backend_pdf (part of matplotlib)
"""

import os
import numpy as np
import pandas as pd
import scipy.signal as sps
import scipy.interpolate as interp
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages # Import for multi-page PDF

# -----------------------------
# USER PARAMETERS (EDIT AS NEEDED)
# -----------------------------
FILEPATH = r'D:\Project\Avtec\Data\Avtec_GearBoxNVH\Load_fifty_percent\measurement.csv'

# Column names in the CSV. Update if your CSV uses different headers.
COL_TIME = None           
COL_RPM = 'RPM'          
VIB_CHANNELS = ['Pinion_y']  

# If your CSV doesn't include time stamps, set COL_TIME = None and provide Fs:
Fs = 50000              # samples/sec (set if COL_TIME is None). Example: Fs = 20000

# Analysis parameters
samples_per_rev = 1024    
min_samples_per_rev = 200 
interp_kind = 'cubic'     
window_fn = np.hanning    
nfft = None               
save_results_folder = os.path.join(os.path.dirname(FILEPATH), 'order_tracking_results')
# --- NEW PARAMETER ---
# Base name for the saved files
OUTPUT_BASENAME = os.path.basename(FILEPATH).replace('.csv','')

# -----------------------------
# Helper functions
# -----------------------------
def read_csv_guess(filepath, col_time, col_rpm, vib_chs):
    df = pd.read_csv(filepath, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    
    if col_time in df.columns:
        df[col_time] = df[col_time].astype(str).str.replace('s', '').str.strip()
        df[col_time] = pd.to_numeric(df[col_time], errors='coerce')
        df[col_time] = df[col_time].interpolate()
    
    if col_rpm in df.columns:
        df[col_rpm] = pd.to_numeric(df[col_rpm], errors='coerce')
    
    for ch in vib_chs:
        if ch in df.columns:
            df[ch] = pd.to_numeric(df[ch], errors='coerce')
    
    missing = []
    for c in vib_chs + ([col_time] if col_time else []) + [col_rpm]:
        if c and c not in df.columns:
            missing.append(c)
    if missing:
        raise ValueError(f"Columns not found in CSV: {missing}. Available columns: {df.columns.tolist()}")
    
    return df

def ensure_time_vector(df, col_time, Fs):
    if col_time and col_time in df.columns:
        t = df[col_time].values
        if np.any(np.diff(t) <= 0):
            raise ValueError("Time column is not strictly increasing")
        return t
    else:
        if Fs is None:
            raise ValueError("No time column and Fs is not provided. Set Fs or include a Time column.")
        n = len(df)
        return np.arange(n) / float(Fs)

def rpm_to_angle(rpm, t):
    # Use the RPM channel specified by COL_RPM
    f = rpm / 60.0
    cycles = np.concatenate([[0.0], np.cumsum((f[:-1] + f[1:]) / 2.0 * np.diff(t))])
    theta = 2.0 * np.pi * cycles
    return theta

def angular_resample_single_channel(vib, t_vib, theta_vib, samples_per_rev, interp_kind='cubic', min_samples_per_rev=16):
    rev_index = np.floor(theta_vib / (2.0 * np.pi)).astype(int)
    max_rev = int(rev_index.max())
    n_rev = max_rev
    if n_rev <= 0:
        # This is the line that throws the error.
        raise ValueError("Not enough revolutions found in theta. Check RPM/time alignment.") 
    angle_grid = np.linspace(0, 2.0*np.pi, samples_per_rev, endpoint=False)
    rev_center_time = np.zeros(n_rev)
    rev_mean_rpm = np.zeros(n_rev)
    for r in range(n_rev):
        mask = rev_index == r
        if mask.sum() < max(min_samples_per_rev, 8):
            continue
        t_r = t_vib[mask]
        theta_r = theta_vib[mask] - r * 2.0*np.pi
        vib_r = vib[mask]
        order = np.argsort(theta_r)
        theta_r = theta_r[order]
        vib_r = vib_r[order]
        try:
            f_interp = interp.interp1d(theta_r, vib_r, kind=interp_kind, bounds_error=False, fill_value='extrapolate')
            resampled[r, :] = f_interp(angle_grid)
        except Exception:
            f_interp = interp.interp1d(theta_r, vib_r, kind='linear', bounds_error=False, fill_value='extrapolate')
            resampled[r, :] = f_interp(angle_grid)
        rev_center_time[r] = t_r.mean()
        theta_span = theta_r[-1] - theta_r[0] + 1e-12
        time_span = t_r[-1] - t_r[0] + 1e-12
        rev_mean_rpm[r] = (theta_span / (2.0*np.pi)) / time_span * 60.0
    return resampled, angle_grid, rev_center_time, rev_mean_rpm

# -----------------------------
# MAIN PROCESS
# -----------------------------
# -----------------------------
# MAIN PROCESS (Corrected)
# -----------------------------
def main():
    print("Reading CSV...")
    df = read_csv_guess(FILEPATH, COL_TIME, COL_RPM, VIB_CHANNELS)
    t = ensure_time_vector(df, COL_TIME, Fs)
    dt = np.median(np.diff(t))
    Fs_detected = 1.0 / dt
    print(f"Detected Fs (from time vector) = {Fs_detected:.3f} Hz")

    # Read and align RPM
    rpm_series = df[COL_RPM].values.astype(float)
    if len(rpm_series) == len(t):
        rpm_on_vib = rpm_series
    else:
        print("RPM channel length differs from vibration samples. Interpolating RPM to vibration times.")
        n_rpm = len(rpm_series)
        t_rpm = np.linspace(t[0], t[-1], n_rpm)
        rpm_on_vib = np.interp(t, t_rpm, rpm_series)

    # VITAL FIX: Load raw vibration channels directly BEFORE plotting/resampling 
    # This block was moved up to resolve the NameError.
    vib_data = {}
    for ch in VIB_CHANNELS:
        print(f"Loading raw data for channel: {ch}")
        vib_data[ch] = df[ch].values.astype(float) # Defines vib_data dictionary

    # Build theta(t)
    print("Converting RPM to continuous angle theta(t) ...")
    theta = rpm_to_angle(rpm_on_vib, t)

    # Create output folder
    os.makedirs(save_results_folder, exist_ok=True)
    
    # Initialize multi-page PDF writer
    pdf_filepath = os.path.join(save_results_folder, f'{OUTPUT_BASENAME}_OrderTracking_Results.pdf')
    print(f"Initializing PDF writer: {pdf_filepath}")
    
    with PdfPages(pdf_filepath) as pdf:
        
        # --- FIGURE 1: Recorded RPM (QC) ---
        fig1 = plt.figure(figsize=(8,3))
        # This code uses rpm_on_vib, which is defined above.
        plt.plot(t, rpm_on_vib, label='RPM')
        plt.xlabel('Time [s]'); plt.ylabel('RPM'); plt.title('Recorded RPM (QC)')
        plt.grid(True); plt.tight_layout()
        pdf.savefig(fig1) 
        fig1.savefig(os.path.join(save_results_folder, f'{OUTPUT_BASENAME}_RPM_Trace.png')) 
        plt.close(fig1)

        # Angular resampling per channel
        # This loop now safely uses vib_data and theta.
        for ch in VIB_CHANNELS: 
            vib = vib_data[ch] # NO LONGER CAUSES NAMEERROR!
            print(f"Angular resampling channel: {ch}")
            # ... rest of the code ...
            resampled_matrix, angle_grid, rev_center_time, rev_mean_rpm = angular_resample_single_channel(
                vib, t, theta, samples_per_rev=samples_per_rev, interp_kind=interp_kind,
                min_samples_per_rev=min_samples_per_rev
            )
            n_rev, n_ang = resampled_matrix.shape
            print(f"Resampled into {n_rev} revolutions x {n_ang} samples_per_rev")

            # Compute FFT on each revolution
            fft_len = n_ang if nfft is None else nfft
            window = window_fn(n_ang)
            order_spectra = np.fft.rfft(resampled_matrix * window[np.newaxis, :], n=fft_len, axis=1)
            order_magnitude = np.abs(order_spectra)
            orders = np.fft.rfftfreq(fft_len, d=1.0/n_ang)
            order_db = 20.0 * np.log10(order_magnitude + 1e-12)

            # --- FIGURE 2: Order map (WaterFall) ---
            fig2 = plt.figure(figsize=(9,5))
            extent = [0, n_rev, orders[0], orders[-1]]
            plt.imshow(order_db.T, aspect='auto', origin='lower', extent=extent, cmap='viridis')
            plt.colorbar(label='Amplitude [dB]')
            plt.xlabel('Revolution index'); plt.ylabel('Order'); plt.title(f'Order map (channel {ch})')
            plt.tight_layout()
            pdf.savefig(fig2) # Save to PDF
            fig2.savefig(os.path.join(save_results_folder, f'{OUTPUT_BASENAME}_{ch}_OrderMap.png')) # Save to PNG
            plt.close(fig2)

            # --- FIGURE 3: Order tracks ---
            fig3 = plt.figure(figsize=(8,4))
            orders_of_interest = [1,2,3,4,5,6]
            for ord_ in orders_of_interest:
                idx = np.argmin(np.abs(orders - ord_))
                amp = order_magnitude[:, idx]
                plt.plot(rev_mean_rpm, amp, label=f'Order {ord_}')
            plt.xlabel('RPM'); plt.ylabel('Amplitude'); plt.title(f'Order tracks (channel {ch})'); plt.grid(True)
            plt.legend()
            plt.tight_layout()
            pdf.savefig(fig3) # Save to PDF
            fig3.savefig(os.path.join(save_results_folder, f'{OUTPUT_BASENAME}_{ch}_OrderTracks.png')) # Save to PNG
            plt.close(fig3)

            # Save NumPy results
            out_prefix = os.path.join(save_results_folder, f"{OUTPUT_BASENAME}_{ch}")
            np.save(out_prefix + '_order_map.npy', order_magnitude)
            np.save(out_prefix + '_orders.npy', orders)
            np.save(out_prefix + '_rev_rpm.npy', rev_mean_rpm)
            print(f"Saved order data to {out_prefix}_*.npy")
    
    # Final cleanup (optional, but good practice)
    plt.close('all') 
    print(f"All figures saved to {pdf_filepath}")
    print("DONE.")

if __name__ == '__main__':
    main()