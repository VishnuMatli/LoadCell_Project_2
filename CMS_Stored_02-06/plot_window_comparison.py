#!/usr/bin/env python3
"""Plot comparison of windowing method outputs.

Searches for files named like `filtered_<window>_<base>.txt` in the project root
and parent directory, loads them, overlays time-domain traces and FFT spectra,
and writes a PNG per base filename into `plots/` (created if missing).

Usage:
  python plot_window_comparison.py --base 535g20250502pm427ms20hz0.txt
  python plot_window_comparison.py --all

"""
import os
import glob
import re
import argparse
import sys
import numpy as np
import matplotlib
# If the user requested an interactive show (via --show), don't force Agg backend.
# Check command-line early so backend can be selected before pyplot import.
show_flag = '--show' in sys.argv or '--gui' in sys.argv
if not show_flag:
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Calibration constants (match C code)
ADC_MAX_VAL_FLOAT = 2147483648.0
ZERO_CAL = 0.01823035255075
SCALE_CAL = 0.00000451794631


def find_filtered_files_for_base(base):
    # Look in current dir and parent dir
    pattern = f"filtered_*{base}"
    files = glob.glob(pattern)
    if not files:
        files = glob.glob(os.path.join('..', pattern))
    return sorted(files)


def infer_base_names():
    # Collect unique base filenames from filtered_* files
    files = glob.glob('filtered_*') + glob.glob(os.path.join('..', 'filtered_*'))
    bases = set()
    for f in files:
        m = re.match(r'filtered_[^_]+_(.+)$', os.path.basename(f))
        if m:
            bases.add(m.group(1))
    return sorted(bases)


def load_floats(filepath):
    data = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(float(line))
                except ValueError:
                    # try to extract first number in line
                    m = re.search(r'-?\d+\.?\d*', line)
                    if m:
                        data.append(float(m.group(0)))
    except FileNotFoundError:
        return None
    return np.array(data, dtype=float)


def load_raw_from_adc(base):
    candidates = [
        os.path.join('adc_data', base),
        os.path.join('client_files', base),
        base,
        os.path.join('..', 'adc_data', base),
        os.path.join('..', 'client_files', base),
        os.path.join('..', base)
    ]
    for p in candidates:
        if os.path.exists(p):
            vals = []
            with open(p, 'r') as f:
                for line in f:
                    m = re.search(r'-?\d+', line)
                    if m:
                        try:
                            vals.append(int(m.group(0)))
                        except ValueError:
                            continue
            if vals:
                arr = np.array([(v / ADC_MAX_VAL_FLOAT - ZERO_CAL) / SCALE_CAL for v in vals], dtype=float)
                return arr
    return None


def compute_single_sided_spectrum(x, fs):
    N = len(x)
    if N == 0:
        return np.array([]), np.array([])
    X = np.fft.fft(x * np.hamming(N))
    freqs = np.fft.fftfreq(N, d=1.0/fs)
    pos = N // 2 + 1
    freqs_pos = freqs[:pos]
    mag = np.abs(X[:pos])
    # scale
    if N > 0:
        mag[0] = mag[0] / N
        if N % 2 == 0 and pos > 1:
            mag[-1] = mag[-1] / N
            mag[1:-1] = 2 * mag[1:-1] / N
        else:
            mag[1:] = 2 * mag[1:] / N
    return freqs_pos, mag


def plot_comparison_for_base(base, samplerate=1000.0, save_dir='plots', show=False):
    files = find_filtered_files_for_base(base)
    if not files:
        print(f"No filtered files found for base: {base}")
        return False

    os.makedirs(save_dir, exist_ok=True)

    # Load filtered signals
    window_signals = {}
    for f in files:
        name = os.path.basename(f)
        # filename format: filtered_<window>_<base>
        m = re.match(r'filtered_([^_]+)_(.+)', name)
        if m:
            window = m.group(1)
        else:
            window = name
        data = load_floats(f)
        if data is None or data.size == 0:
            print(f"Warning: could not load data from {f}")
            continue
        window_signals[window] = data

    if not window_signals:
        print(f"No window signals loaded for {base}")
        return False

    # Try to load raw weights (normalized) from adc_data
    raw = load_raw_from_adc(base)

    # Create figure
    plt.close('all')
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # Time-domain: raw
    if raw is not None:
        axes[0].plot(raw, 'r-', label='Raw (normalized)')
        axes[0].set_title(f"Raw ADC Data - {base}")
        axes[0].legend()
    else:
        axes[0].set_title(f"Raw ADC Data - (not found) {base}")

    # Time-domain: filtered overlays (truncate to shortest length for fair overlay)
    minlen = min([len(v) for v in window_signals.values()])
    for w, sig in sorted(window_signals.items()):
        axes[1].plot(np.arange(minlen), sig[:minlen], label=w)
    axes[1].set_title(f"FIR-Filtered comparison - {base}")
    axes[1].legend()

    # FFT overlays of filtered signals
    for w, sig in sorted(window_signals.items()):
        freqs, mag = compute_single_sided_spectrum(sig[:minlen], samplerate)
        if freqs.size > 0:
            axes[2].plot(freqs, mag, label=w)
    axes[2].set_title(f"FFT Spectrum comparison - {base}")
    axes[2].set_xlim(0, samplerate/2)
    axes[2].legend()

    plt.tight_layout()
    outpath = os.path.join(save_dir, f"comparison_{os.path.splitext(base)[0]}.png")
    fig.savefig(outpath)
    print(f"Saved comparison plot to: {outpath}")
    if show:
        try:
            plt.show()
        except Exception as e:
            print(f"Could not open interactive window: {e}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Compare windowing outputs (filtered_* files)')
    parser.add_argument('--base', help='Base filename to compare (e.g. 535g...20hz0.txt)')
    parser.add_argument('--all', action='store_true', help='Process all bases found')
    parser.add_argument('--samplerate', type=float, default=1000.0, help='Sampling rate for FFT (Hz)')
    parser.add_argument('--out', default='plots', help='Output directory for PNGs')
    parser.add_argument('--show', action='store_true', help='Open interactive window to display the comparison')
    args = parser.parse_args()

    if not args.base and not args.all:
        # try to infer bases and prompt
        bases = infer_base_names()
        if not bases:
            print('No filtered_* files found in current or parent directory. Nothing to do.')
            return
        print('Available bases:')
        for i, b in enumerate(bases, 1):
            print(f"  {i}) {b}")
        choice = input('Pick a base number to plot (or press Enter to process all): ').strip()
        if choice == '':
            args.all = True
        else:
            try:
                idx = int(choice) - 1
                args.base = bases[idx]
            except Exception:
                print('Invalid selection')
                return

    bases_to_process = []
    if args.all:
        bases_to_process = infer_base_names()
    else:
        bases_to_process = [args.base]

    if not bases_to_process:
        print('No bases to process')
        return

    for base in bases_to_process:
        plot_comparison_for_base(base, samplerate=args.samplerate, save_dir=args.out, show=args.show)


if __name__ == '__main__':
    main()
