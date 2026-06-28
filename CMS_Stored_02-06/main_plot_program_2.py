import os
import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
import threading
import time
from collections import deque

# Plot behavior
PLOT_WINDOW_SIZE = 500
DEFAULT_INTERVAL_MS = 20

# Calibration constants (same as C code)
ADC_MAX_VAL_FLOAT = 2147483648.0
ZERO_CAL = 0.01823035255075
SCALE_CAL = 0.00000451794631

WINDOW_METHODS = [
    "triangular",
    "rectangular",
    "hamming",
    "hanning",
    "blackman",
    "kaiser",
    "parks_mcclellan",
    "frequency_sampling",
    "least_squares",
]
SPEED_OPTIONS = ["5ms", "10ms", "20ms", "50ms", "100ms"]
DEFAULT_COEFF_COUNT = 11
CUTOFF_FREQ_HZ = 10.0
SAMPLING_FREQ_HZ = 50.0
KAISER_BETA = 5.0
FILTER_START_DELAY_MS = 2000


def get_frame_step(interval_ms):
    # Larger step for smaller interval makes speed differences clearly visible.
    if interval_ms <= 5:
        return 10
    if interval_ms <= 10:
        return 5
    if interval_ms <= 20:
        return 2
    return 1

# FIR filter implementation (direct form)
class FIRFilter:
    def __init__(self, coeffs):
        self.coeffs = np.array(coeffs, dtype=float)
        self.state = np.zeros(len(self.coeffs) - 1, dtype=float)  # Delay line
    
    def filter(self, sample):
        # Direct form FIR: y[n] = sum(b[k] * x[n-k])
        x = np.insert(self.state, 0, sample)  # New sample at front
        y = np.dot(self.coeffs, x)
        self.state = x[:-1]  # Update delay line
        return y

# Global state
g_root = None
g_canvas = None
g_status_var = None
g_bandwidth_var = None
g_file_var = None
g_window_var = None
g_speed_var = None
g_available_files = []
g_available_windows = []
g_base_filename = ""
g_selected_window = "rectangular"

# Data buffers (FIXED LENGTH for real-time oscilloscope behavior)
raw_buffer = deque(maxlen=PLOT_WINDOW_SIZE)
ref_filtered_buffer = deque(maxlen=PLOT_WINDOW_SIZE)   # Reference filter (selected window method)
manual_filtered_buffer = deque(maxlen=PLOT_WINDOW_SIZE)  # Manual FIR filter (if enabled)
data_lock = threading.Lock()

# Filter objects
ref_filter = None
manual_filter = None
manual_mode = False

# Thread control
stream_thread = None
stop_thread = False
stream_started = False

# Plot objects
fig = None
axes = None
raw_line = None
filtered_line = None
manual_filtered_line = None
control_frame = None
stats_frame = None
sidebar_canvas = None
sidebar_scrollbar = None
sidebar_inner = None

g_coeff_count_var = None
g_filtered_only_var = None
g_raw_axes_pos = None
g_filtered_axes_pos = None
g_filtered_only_axes_pos = None

g_animation = None
g_plot_running = False
g_interval_ms = DEFAULT_INTERVAL_MS

def normalize_adc_to_weights(adc_values):
    adc_arr = np.array(adc_values, dtype=float)
    return (adc_arr / ADC_MAX_VAL_FLOAT - ZERO_CAL) / SCALE_CAL

def list_available_input_files():
    discovered = []
    for folder in ("adc_data", "client_files"):
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if name.lower().endswith(".txt"):
                discovered.append(name)
    return sorted(dict.fromkeys(discovered))

# In real-time mode, all window methods are available (we generate filters on-the-fly)
def available_windows_for_file(base_filename):
    return WINDOW_METHODS.copy()

def choose_default_window(base_filename, preferred_window=None):
    windows = available_windows_for_file(base_filename)
    if preferred_window in windows:
        return preferred_window, windows
    if windows:
        return windows[0], windows
    return (preferred_window if preferred_window in WINDOW_METHODS else WINDOW_METHODS[0], windows)

# Moved these up to be defined before generate_window_coefficients
def _normalized_sinc(n, alpha, cutoff_freq=CUTOFF_FREQ_HZ, sampling_freq=SAMPLING_FREQ_HZ):
    fc = cutoff_freq / sampling_freq
    if abs(float(n) - float(alpha)) < 1e-9:
        return 2.0 * fc
    return np.sin(2.0 * np.pi * fc * (float(n) - float(alpha))) / (np.pi * (float(n) - float(alpha)))

def _kaiser_i0(x):
    total = 1.0
    term = 1.0
    half_x = 0.5 * x
    for k in range(1, 21):
        term *= (half_x * half_x) / (float(k) * float(k))
        total += term
        if term < 1e-8:
            break
    return total

def generate_window_coefficients(window_method, num_taps):
    num_taps = int(num_taps)
    if num_taps < 2:
        raise ValueError("Number of coefficients must be at least 2.")
    alpha = (num_taps - 1) / 2.0
    coeffs = np.zeros(num_taps, dtype=float)
    gain = 0.0

    for n in range(num_taps):
        sinc_val = _normalized_sinc(n, alpha)

        if window_method == "rectangular":
            window_value = 1.0
        elif window_method == "triangular":
            window_value = 1.0 - 2.0 * abs(float(n) - alpha) / (num_taps - 1)
        elif window_method == "hamming":
            window_value = 0.54 - 0.46 * np.cos(2.0 * np.pi * n / (num_taps - 1))
        elif window_method == "hanning":
            window_value = 0.5 - 0.5 * np.cos(2.0 * np.pi * n / (num_taps - 1))
        elif window_method == "blackman":
            window_value = (
                0.42
                - 0.5 * np.cos(2.0 * np.pi * n / (num_taps - 1))
                + 0.08 * np.cos(4.0 * np.pi * n / (num_taps - 1))
            )
        elif window_method == "kaiser":
            ratio = (float(n) - alpha) / alpha if alpha != 0 else 0.0
            inside = max(0.0, 1.0 - ratio * ratio)
            window_value = _kaiser_i0(KAISER_BETA * np.sqrt(inside)) / _kaiser_i0(KAISER_BETA)
        else:
            window_value = 0.54 - 0.46 * np.cos(2.0 * np.pi * n / (num_taps - 1))

        coeffs[n] = sinc_val * window_value
        gain += coeffs[n]

    if abs(gain) > 1e-12:
        coeffs /= gain
    return coeffs

def start_data_stream(filename, window_method, coeff_count):
    """Start background thread to read file and apply filters in REAL-TIME with 20ms/sample timing."""
    global stream_thread, stop_thread, stream_started, ref_filter, manual_filter, manual_mode
    global raw_buffer, ref_filtered_buffer, manual_filtered_buffer
    
    # Stop any existing stream
    stop_data_stream()
    
    # Clear buffers (reset to empty)
    with data_lock:
        raw_buffer.clear()
        ref_filtered_buffer.clear()
        manual_filtered_buffer.clear()
    
    # Reset flags
    stop_thread = False
    stream_started = True
    
    # Create filters ONCE at startup (not per sample)
    try:
        ref_coeffs = generate_window_coefficients(window_method, coeff_count)
        ref_filter = FIRFilter(ref_coeffs)  # Reference filter (selected window method)
        manual_filter = None  # Will be created when user applies manual coeffs
        manual_mode = False
    except Exception as e:
        print(f"[APP] Failed to create reference filter: {e}")
        return False
    
    # Find file path
    base_filename = os.path.basename(filename)
    candidates = [
        os.path.join("adc_data", base_filename),
        os.path.join("client_files", base_filename),
        base_filename,
        os.path.join("..", "adc_data", base_filename),
        os.path.join("..", "client_files", base_filename),
        os.path.join("..", base_filename),
    ]
    filepath = None
    for path in candidates:
        if os.path.exists(path):
            filepath = path
            break
    if not filepath:
        print(f"[APP] File not found: {filename}")
        return False
    
    # START REAL-TIME PROCESSING THREAD
    def stream_worker():
        """This thread simulates LIVE load cell data: reads 1 sample every 20ms (50Hz)"""
        try:
            with open(filepath, 'r') as f:
                # Process file LINE BY LINE as if it's streaming from a real load cell
                for line in f:
                    # CHECK IF WE SHOULD STOP (user changed file/settings)
                    if stop_thread:
                        break
                    
                    # EXTRACT ADC VALUE FROM LINE (simulating digital input from load cell)
                    m = re.search(r"-?\d+", line)
                    if m:
                        try:
                            # 1. GET DIGITAL ADC VALUE FROM LOAD CELL (SIMULATED)
                            adc_raw = int(m.group(0))
                            
                            # 2. CONVERT DIGITAL → ANALOG WEIGHT (using your calibration constants)
                            weight_analog = normalize_adc_to_weights([adc_raw])[0]
                            
                            # =========================================================
                            # REAL-TIME TWO-PATH SIGNAL PROCESSING (PER SAMPLE)
                            # =========================================================
                            
                            # PATH 1: RAW DATA (unfiltered weight for raw plot)
                            with data_lock:
                                raw_buffer.append(weight_analog)  # Send directly to raw plot
                            
                            # PATH 2: FILTERED DATA (weight → FIR filter → filtered plot)
                            with data_lock:
                                # Apply REFERENCE FIR FILTER (always active - your selected window method)
                                if ref_filter is not None:
                                    filtered_weight = ref_filter.filter(weight_analog)
                                    ref_filtered_buffer.append(filtered_weight)
                                
                                # Apply MANUAL FIR FILTER (only if user activated it)
                                if manual_mode and manual_filter is not None:
                                    manual_filtered = manual_filter.filter(weight_analog)
                                    manual_filtered_buffer.append(manual_filtered)
                                # NOTE: When manual mode is OFF, we don't touch manual buffer
                                # (it will show last valid manual filter output or be empty)
                            
                        except ValueError:
                            continue  # Skip invalid lines
                    
                    # 3. SIMULATE REAL-TIME TIMING: 20ms PER SAMPLE (50Hz load cell rate)
                    # This is CRITICAL - ensures processing matches real load cell timing
                    time.sleep(0.02)  # 20ms = 50Hz sampling rate
                    
        except Exception as e:
            print(f"[APP] Stream error: {e}")
        finally:
            global stream_started
            stream_started = False  # Mark stream as stopped
    
    # LAUNCH THE REAL-TIME PROCESSING THREAD
    stream_thread = threading.Thread(target=stream_worker, daemon=True)
    stream_thread.start()
    return True

def stop_data_stream():
    """Stop the background streaming thread."""
    global stream_thread, stop_thread, stream_started
    stop_thread = True
    if stream_thread is not None and stream_thread.is_alive():
        stream_thread.join(timeout=1.0)
    stream_thread = None
    stream_started = False

def has_manual_output():
    return manual_mode and manual_filter is not None and len(manual_filtered_buffer) > 0

def current_filtered_series():
    if has_manual_output():
        return list(manual_filtered_buffer)
    else:
        return list(ref_filtered_buffer)

def get_buffer_lengths():
    with data_lock:
        return len(raw_buffer), len(ref_filtered_buffer), len(manual_filtered_buffer)

def calculate_bandwidth(series):
    if series is None or len(series) == 0:
        return 0.0
    return float(np.nanmax(series) - np.nanmin(series))

def is_filtered_only_mode():
    return bool(g_filtered_only_var.get()) if g_filtered_only_var is not None else False

def update_filter_summary():
    raw_len, ref_len, man_len = get_buffer_lengths()
    raw_list = list(raw_buffer) if raw_len > 0 else []
    ref_list = list(ref_filtered_buffer) if ref_len > 0 else []
    man_list = list(manual_filtered_buffer) if man_len > 0 else []
    
    raw_bw = calculate_bandwidth(raw_list)
    ref_bw = calculate_bandwidth(ref_list)
    man_bw = calculate_bandwidth(man_list) if man_len > 0 else 0.0
    
    display_bw = man_bw if has_manual_output() else ref_bw
    
    if g_bandwidth_var is not None:
        if is_filtered_only_mode():
            if has_manual_output():
                g_bandwidth_var.set(
                    f"Filtered bandwidth: {display_bw:.2f}    |    Manual taps: {len(manual_filter.coeffs) if manual_filter else 0}"
                )
            else:
                g_bandwidth_var.set(f"Filtered bandwidth: {display_bw:.2f}")
        else:
            if has_manual_output():
                g_bandwidth_var.set(
                    f"Raw bandwidth: {raw_bw:.2f}    |    Reference: {ref_bw:.2f}    |    Manual: {display_bw:.2f}"
                )
            else:
                g_bandwidth_var.set(
                    f"Raw bandwidth: {raw_bw:.2f}    |    Filtered bandwidth: {display_bw:.2f}"
                )
    update_status_text()

def update_status_text(prefix=None):
    base = f"File: {g_base_filename} | Window: {g_selected_window} | Speed: {g_interval_ms} ms"
    if has_manual_output():
        coeffs_len = len(manual_filter.coeffs) if manual_filter else 0
        base += f" | Manual coeffs ON ({coeffs_len} taps)"
    if prefix:
        return f"{prefix} | {base}"
    return base

def update_display_mode():
    if axes is None:
        return
    
    filtered_only = is_filtered_only_mode()
    
    if filtered_only:
        if axes[0] is not None:
            axes[0].set_visible(True)
            axes[0].set_position(g_raw_axes_pos)
        axes[1].set_position(g_filtered_axes_pos)
        raw_line.set_visible(False)
        filtered_line.set_visible(True)
        manual_filtered_line.set_visible(False)
        
        active_filtered_label = "Filtered Output"
        if has_manual_output():
            active_filtered_label = f"Manual FIR Output ({len(manual_filter.coeffs) if manual_filter else 0} taps)"
        else:
            active_filtered_label = "FIR Filtered Data"
        
        filtered_line.set_color("#1f6feb")
        filtered_line.set_linestyle("-")
        filtered_line.set_linewidth(1.8)
        filtered_line.set_label(active_filtered_label)
        axes[0].set_title(f"Raw ADC Data - {os.path.basename(g_base_filename)}", fontsize=12, weight="bold", color="#243043")
        axes[0].set_ylabel("Weight", color="#243043")
        axes[1].set_title(f"Filtered Data - {os.path.basename(g_base_filename)}", fontsize=12, weight="bold", color="#243043")
        axes[1].set_xlabel("Sample Index", color="#243043")
        axes[1].set_ylabel("Weight", color="#243043")
        axes[1].legend(loc="upper right", frameon=True, facecolor="white")
        return
    
    if axes[0] is not None:
        axes[0].set_visible(True)
        axes[0].set_position(g_raw_axes_pos)
    axes[1].set_position(g_filtered_axes_pos)
    raw_line.set_visible(True)
    
    if has_manual_output():
        filtered_line.set_visible(True)
        manual_filtered_line.set_visible(True)
        filtered_line.set_color("#7d8794")
        filtered_line.set_linestyle("--")
        filtered_line.set_linewidth(1.4)
        filtered_line.set_label("Reference Filtered")
        manual_filtered_line.set_color("#1f6feb")
        manual_filtered_line.set_linestyle("-")
        manual_filtered_line.set_linewidth(1.9)
        manual_filtered_line.set_label(f"Manual FIR Output ({len(manual_filter.coeffs) if manual_filter else 0} taps)")
        axes[1].set_title(f"Manual FIR Filtered Data vs Reference - {os.path.basename(g_base_filename)}", fontsize=12, weight="bold", color="#243043")
    else:
        filtered_line.set_visible(True)
        manual_filtered_line.set_visible(False)
        filtered_line.set_color("#1f6feb")
        filtered_line.set_linestyle("-")
        filtered_line.set_linewidth(1.8)
        filtered_line.set_label("FIR Filtered Data")
        manual_filtered_line.set_label("Manual FIR Output")
        axes[1].set_title(f"FIR Filtered Data - {os.path.basename(g_base_filename)}", fontsize=12, weight="bold", color="#243043")

    axes[1].legend(loc="upper right", frameon=True, facecolor="white")

def recompute_manual_output():
    """Not used in streaming mode - kept for compatibility"""
    pass

def update_plot_titles():
    base = os.path.basename(g_base_filename)
    if axes is not None:
        axes[0].set_title(f"Raw ADC Data - {base}")
        if has_manual_output():
            axes[1].set_title(f"Manual FIR Filtered Data vs Reference - {base}")
        else:
            axes[1].set_title(f"FIR Filtered Data ({g_selected_window}) - {base}")

def set_visible_limits(current_length):
    """
    Update axis limits dynamically for raw and filtered plots.
    Offsets the filtered plot X-axis by the filter's group delay.
    """
    # 1. Get buffer stats and determine filter delay (Taps/2)
    raw_len, ref_len, man_len = get_buffer_lengths()
    taps = len(manual_filter.coeffs) if manual_mode else len(ref_filter.coeffs)
    delay = taps // 2
    
    with data_lock:
        raw_data = list(raw_buffer)
        current_filtered = list(manual_filtered_buffer if has_manual_output() else ref_filtered_buffer)
    
    # 2. X-axis Limits (Raw Data)
    # Standard scrolling window for the raw signal
    raw_x_max = max(PLOT_WINDOW_SIZE, raw_len)
    raw_x_min = max(0, raw_x_max - PLOT_WINDOW_SIZE)
    axes[0].set_xlim(raw_x_min, raw_x_max)
    
    # 3. X-axis Limits (Filtered Data - Offset by Delay)
    # The X-axis for filtered data starts at 'delay' samples
    filt_data_len = len(current_filtered)
    filt_x_max = max(PLOT_WINDOW_SIZE, filt_data_len + delay)
    filt_x_min = max(0, filt_x_max - PLOT_WINDOW_SIZE)
    axes[1].set_xlim(filt_x_min, filt_x_max)
    
    # 4. Y-axis Auto-scaling
    # Raw signal Y-scaling
    if raw_len > 0:
        y_min = np.nanmin(raw_data)
        y_max = np.nanmax(raw_data)
        span = y_max - y_min
        pad = max(span * 0.12, 0.1)
        axes[0].set_ylim(y_min - pad, y_max + pad)
    
    # Filtered signal Y-scaling
    if filt_data_len > 0:
        y_min = np.nanmin(current_filtered)
        y_max = np.nanmax(current_filtered)
        span = y_max - y_min
        pad = max(span * 0.12, 0.1)
        axes[1].set_ylim(y_min - pad, y_max + pad)
        
def init_plot():
    """Initialize the GUI components - MUST BE DEFINED BEFORE MAIN CALLS IT"""
    global fig, axes, raw_line, filtered_line, manual_filtered_line, g_canvas, control_frame, stats_frame
    global sidebar_canvas, sidebar_scrollbar, sidebar_inner, g_coeff_count_var, g_filtered_only_var
    global g_raw_axes_pos, g_filtered_axes_pos, g_filtered_only_axes_pos
    
    plt.close("all")
    fig = Figure(figsize=(12, 8), dpi=100)
    axes = fig.subplots(2, 1)
    fig.patch.set_facecolor("#eef3fb")
    fig.subplots_adjust(left=0.14, bottom=0.10, right=0.98, top=0.95, hspace=0.34)

    raw_line, = axes[0].plot([], [], color="#e4572e", linewidth=1.8, label="Raw Data")
    filtered_line, = axes[1].plot([], [], color="#1f6feb", linewidth=1.8, label="FIR Filtered Data")
    manual_filtered_line, = axes[1].plot([], [], color="#1f6feb", linewidth=1.8, linestyle="-", label="Manual FIR Output")
    manual_filtered_line.set_visible(False)

    for axis, face, spine in (
        (axes[0], "#fff5ef", "#e4572e"),
        (axes[1], "#f3f8ff", "#1f6feb"),
    ):
        axis.set_facecolor(face)
        axis.grid(True, color="#cfd8e3", alpha=0.8, linestyle="--", linewidth=0.7)
        for side in axis.spines.values():
            side.set_color(spine)
            side.set_linewidth(1.1)

    axes[0].set_title("Raw ADC Data", fontsize=12, weight="bold", color="#243043")
    axes[0].set_ylabel("Weight", color="#243043")
    axes[0].legend(loc="upper right", facecolor="white")

    axes[1].set_title("FIR Filtered Data", fontsize=12, weight="bold", color="#243043")
    axes[1].set_xlabel("Sample Index", color="#243043")
    axes[1].set_ylabel("Weight", color="#243043")
    axes[1].legend(loc="upper right", frameon=True, facecolor="white")

    g_raw_axes_pos = axes[0].get_position().frozen()
    g_filtered_axes_pos = axes[1].get_position().frozen()
    g_filtered_only_axes_pos = [g_filtered_axes_pos.x0, g_raw_axes_pos.y0, g_filtered_axes_pos.width, g_raw_axes_pos.height + g_filtered_axes_pos.height + 0.08]

    main_frame = tk.Frame(g_root, bg="#eef3fb")
    main_frame.pack(fill=tk.BOTH, expand=True)
    main_frame.grid_columnconfigure(0, weight=0, minsize=280)
    main_frame.grid_columnconfigure(1, weight=1)
    main_frame.grid_rowconfigure(0, weight=1)
    main_frame.grid_rowconfigure(1, weight=0)

    control_frame = tk.Frame(main_frame, bg="#1f2d3d", width=280)
    control_frame.grid(row=0, column=0, rowspan=2, sticky="nsw")
    control_frame.grid_propagate(False)

    plot_frame = tk.Frame(main_frame, bg="#eef3fb")
    plot_frame.grid(row=0, column=1, sticky="nsew")

    stats_frame = tk.Frame(main_frame, bg="#dce8f7", height=56)
    stats_frame.grid(row=1, column=1, sticky="ew")
    stats_frame.grid_propagate(False)

    g_canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    g_canvas.draw_idle()
    g_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    bandwidth_label = tk.Label(
        stats_frame,
        textvariable=g_bandwidth_var,
        bg="#dce8f7",
        fg="#243043",
        font=("TkDefaultFont", 10, "bold"),
        anchor="w",
        padx=16,
    )
    bandwidth_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    status_label = tk.Label(
        stats_frame,
        textvariable=g_status_var,
        bg="#dce8f7",
        fg="#40526b",
        font=("TkDefaultFont", 9),
        anchor="e",
        padx=16,
    )
    status_label.pack(side=tk.RIGHT, fill=tk.X, expand=True)

    header = tk.Label(
        control_frame,
        text="ADC Controls",
        bg="#17202b",
        fg="white",
        font=("TkDefaultFont", 13, "bold"),
        pady=12,
    )
    header.pack(fill=tk.X)

    sidebar_canvas = tk.Canvas(control_frame, bg="#1f2d3d", highlightthickness=0)
    sidebar_scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=sidebar_canvas.yview)
    sidebar_inner = tk.Frame(sidebar_canvas, bg="#1f2d3d")
    sidebar_inner.bind(
        "<Configure>",
        lambda _e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")),
    )
    sidebar_canvas.create_window((0, 0), window=sidebar_inner, anchor="nw")
    sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
    sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def section_label(text):
        return tk.Label(
            sidebar_inner,
            text=text,
            bg="#1f2d3d",
            fg="#bcd0ea",
            font=("TkDefaultFont", 10, "bold"),
            anchor="w",
            pady=8,
        )

    def styled_combo(parent, variable, values):
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=26)
        combo.pack(fill=tk.X, padx=14, pady=(0, 12))
        return combo

    section_label("Input File").pack(fill=tk.X, padx=14)
    file_combo = styled_combo(sidebar_inner, g_file_var, g_available_files)

    section_label("Window Method").pack(fill=tk.X, padx=14)
    window_combo = styled_combo(sidebar_inner, g_window_var, WINDOW_METHODS)

    section_label("Plot Speed").pack(fill=tk.X, padx=14)
    speed_combo = styled_combo(sidebar_inner, g_speed_var, SPEED_OPTIONS)

    g_filtered_only_var = tk.BooleanVar(value=False)
    filtered_only_check = tk.Checkbutton(
        sidebar_inner,
        text="Plot Only Filtered Data",
        variable=g_filtered_only_var,
        command=on_filtered_only_toggled,
        bg="#1f2d3d",
        fg="#bcd0ea",
        activebackground="#1f2d3d",
        activeforeground="#ffffff",
        selectcolor="#17202b",
        anchor="w",
        padx=14,
        pady=6,
    )
    filtered_only_check.pack(fill=tk.X, padx=14, pady=(0, 10))

    section_label("Number of Coefficients").pack(fill=tk.X, padx=14)
    coeff_help = tk.Label(
        sidebar_inner,
        text="Select the FIR tap count. Coefficients are generated from the chosen window method.",
        bg="#1f2d3d",
        fg="#8aa0bf",
        wraplength=230,
        justify="left",
        pady=4,
    )
    coeff_help.pack(fill=tk.X, padx=14)

    g_coeff_count_var = tk.StringVar(value=str(DEFAULT_COEFF_COUNT))
    coeff_count_spin = tk.Spinbox(
        sidebar_inner,
        from_=2,
        to=201,
        increment=1,
        textvariable=g_coeff_count_var,
        width=10,
        bg="#f7fbff",
        fg="#243043",
        relief="flat",
        justify="left",
    )
    coeff_count_spin.pack(fill=tk.X, padx=14, pady=(0, 10))

    action_panel = tk.Frame(sidebar_inner, bg="#1f2d3d")
    action_panel.pack(fill=tk.X, padx=14, pady=(6, 10))

    def colored_button(text, color, command):
        return tk.Button(
            action_panel,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=8,
        )

    colored_button("Start Plot", "#0c7a46", start_plot).pack(fill=tk.X, pady=(0, 6))
    colored_button("Start Filtered Plot", "#2952a3", start_filtered_plot).pack(fill=tk.X, pady=(0, 6))
    colored_button("Apply Manual Coeffs", "#7b4f01", apply_manual_coeffs_from_controls).pack(fill=tk.X, pady=(0, 6))
    colored_button("Clear Manual Coeffs", "#5f6b7a", clear_manual_coeffs).pack(fill=tk.X, pady=(0, 6))
    colored_button("Pause", "#7b4f01", pause_animation).pack(fill=tk.X, pady=(0, 6))
    colored_button("Resume", "#0c7a46", resume_animation).pack(fill=tk.X, pady=(0, 6))
    colored_button("Reload", "#2952a3", reload_from_controls).pack(fill=tk.X, pady=(0, 6))
    colored_button("Exit", "#a33a3a", g_root.destroy).pack(fill=tk.X)

    help_label = tk.Label(
        sidebar_inner,
        text="Scroll for more options if the window is small.",
        bg="#1f2d3d",
        fg="#8aa0bf",
        wraplength=230,
        justify="left",
        pady=16,
    )
    help_label.pack(fill=tk.X, padx=14)

    file_combo.bind("<<ComboboxSelected>>", on_file_selected)
    window_combo.bind("<<ComboboxSelected>>", on_window_selected)
    speed_combo.bind("<<ComboboxSelected>>", on_speed_selected)

def update_frame(_):
    filtered_only = is_filtered_only_mode()
    
    # Calculate group delay (Taps/2) to align filtered plot with raw data
    taps = len(manual_filter.coeffs) if manual_mode else len(ref_filter.coeffs)
    delay = taps // 2
    
    with data_lock:
        raw_data = list(raw_buffer)
        ref_data = list(ref_filtered_buffer)
        man_data = list(manual_filtered_buffer)
    
    # Plot Raw Data
    if not filtered_only:
        raw_line.set_data(np.arange(len(raw_data)), raw_data)
    else:
        raw_line.set_data([], [])
    
    # Plot Filtered Data with X-axis offset (delay)
    # This removes the "straight line" at the start
    if has_manual_output():
        man_y = man_data
        manual_filtered_line.set_data(np.arange(delay, delay + len(man_y)), man_y)
        filtered_line.set_data([], []) # Hide ref if manual is active
    else:
        ref_y = ref_data
        filtered_line.set_data(np.arange(delay, delay + len(ref_y)), ref_y)
        manual_filtered_line.set_data([], [])

    # Pass the total length including delay to set_visible_limits
    set_visible_limits(len(raw_data) if not filtered_only else len(ref_data) + delay)
    
    return raw_line, filtered_line, manual_filtered_line
def restart_animation():
    global g_animation
    if g_animation and g_animation.event_source:
        g_animation.event_source.stop()
    
    if not g_plot_running:
        if g_canvas is not None:
            g_canvas.draw_idle()
        return
    
    # By setting repeat=True and no frames argument, 
    # it will keep calling update_frame indefinitely.
    g_animation = FuncAnimation(
        fig,
        update_frame,
        interval=g_interval_ms,
        blit=False,
        repeat=True,
    )
    if g_canvas is not None:
        g_canvas.draw_idle()

def apply_manual_coeffs_from_controls():
    global manual_filter, manual_mode
    
    if g_coeff_count_var is None or g_selected_window == "":
        return
    
    try:
        coeff_count = int(g_coeff_count_var.get().strip())
        coeffs = generate_window_coefficients(g_selected_window, coeff_count)
        manual_filter = FIRFilter(coeffs)
        manual_mode = True
    except Exception as exc:
        update_status_text(f"Invalid coefficient count: {exc}")
        return
    
    # IMPORTANT: When manual filter is created, we need to prime it with current buffer state
    # to avoid transient effects. We'll fill the filter state with the last N samples
    # where N = number of taps.
    with data_lock:
        # Clear manual buffer
        manual_filtered_buffer.clear()
        
        # Prime the filter with current raw buffer state (to avoid startup transient)
        if len(raw_buffer) > 0:
            # Get last N samples where N = filter order (taps-1) for proper priming
            primes = list(raw_buffer)[-len(manual_filter.coeffs)+1:] if len(manual_filter.coeffs) > 1 else []
            # Prime the filter state
            for sample in primes:
                manual_filter.filter(sample)
            # Now add current buffer to manual_filtered_buffer
            for sample in raw_buffer:
                manual_filtered_buffer.append(manual_filter.filter(sample))
    
    update_plot_titles()
    update_display_mode()
    update_filter_summary()
    restart_animation()

def on_filtered_only_toggled():
    update_display_mode()
    update_filter_summary()
    restart_animation()

def start_plot():
    global g_plot_running
    g_plot_running = True
    if g_filtered_only_var is not None:
        g_filtered_only_var.set(False)
    update_display_mode()
    update_filter_summary()
    restart_animation()

def start_filtered_plot():
    global g_plot_running
    g_plot_running = True
    if g_filtered_only_var is not None:
        g_filtered_only_var.set(True)
    update_display_mode()
    update_filter_summary()
    restart_animation()

def clear_manual_coeffs():
    global manual_filter, manual_mode
    manual_filter = None
    manual_mode = False
    with data_lock:
        manual_filtered_buffer.clear()
    update_plot_titles()
    update_display_mode()
    update_filter_summary()
    restart_animation()

def reload_filtered_and_restart():
    global g_reference_filtered_data, g_filtered_data
    # Not used in streaming mode - kept for compatibility
    pass

def pause_animation():
    if g_animation and g_animation.event_source:
        g_animation.event_source.stop()
        update_status_text("Paused")

def resume_animation():
    if g_animation and g_animation.event_source:
        g_animation.event_source.start()
        update_status_text("Running")

def reload_from_controls():
    on_file_selected(None)

def on_file_selected(_event):
    global g_base_filename, g_selected_window  # FIXED: Moved global declaration to TOP
    selected_file = g_file_var.get().strip()
    if not selected_file:
        return
    
    # Stop any existing stream
    stop_data_stream()
    
    # Load selected data (starts stream)
    window_method = g_window_var.get().strip() if g_window_var else g_selected_window
    coeff_count = int(g_coeff_count_var.get().strip()) if g_coeff_count_var else DEFAULT_COEFF_COUNT
    
    if start_data_stream(selected_file, window_method, coeff_count):
        g_base_filename = os.path.basename(selected_file)
        g_selected_window = window_method
        if g_window_var is not None:
            g_window_var.set(g_selected_window)
        refresh_available_windows()
        # Start plotting
        g_root.after(500, lambda: start_plot() if not g_plot_running else None)
    else:
        update_status_text(f"Failed to open file: {selected_file}")

def on_window_selected(_event):
    global g_selected_window  # FIXED: Added global declaration
    selected_window = g_window_var.get().strip()
    if selected_window:
        g_selected_window = selected_window  # FIXED: Direct assignment
        reload_filtered_and_restart()

def on_speed_selected(_event):
    selected_speed = g_speed_var.get().strip()
    if selected_speed.endswith("ms"):
        global g_interval_ms
        g_interval_ms = int(selected_speed[:-2])
        if g_animation and g_animation.event_source:
            g_animation.event_source.interval = g_interval_ms
        update_status_text()
        restart_animation()

def refresh_available_windows():
    global g_available_windows
    g_available_windows = WINDOW_METHODS.copy()  # All methods available in real-time
    if g_window_var is not None:
        g_window_var.set(g_selected_window)
    # Only update combobox if GUI is ready
    if sidebar_inner is not None:
        for child in sidebar_inner.winfo_children():
            if isinstance(child, ttk.Combobox) and child.cget("textvariable") == str(g_window_var):
                child['values'] = g_available_windows
                child.set(g_selected_window)
                break

def main():
    global g_root, g_status_var, g_bandwidth_var, g_file_var, g_window_var, g_speed_var, g_available_files
    global g_plot_running
    
    g_available_files = list_available_input_files()
    if not g_available_files:
        print("[APP] No input files found in adc_data/ or client_files/.")
        sys.exit(1)

    initial_file = g_available_files[0]
    if len(sys.argv) >= 2:
        candidate = os.path.basename(sys.argv[1])
        if candidate in g_available_files:
            initial_file = candidate

    g_root = tk.Tk()
    g_root.title("ADC Plotter (Real-time)")
    g_root.geometry("1240x790")
    g_root.minsize(1040, 700)
    g_root.configure(bg="#1f2d3d")

    style = ttk.Style(g_root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TCombobox", padding=6, fieldbackground="#f7fbff", background="#f7fbff")
    style.configure("TButton", padding=6)

    g_status_var = tk.StringVar(value="Loading...")
    g_bandwidth_var = tk.StringVar(value="Bandwidths loading...")
    g_file_var = tk.StringVar(value=initial_file)
    g_window_var = tk.StringVar(value=g_selected_window)  # Initial value: "rectangular"
    g_speed_var = tk.StringVar(value=f"{g_interval_ms}ms")

    # Start initial stream (using initial file and initial window method)
    if start_data_stream(initial_file, g_selected_window, DEFAULT_COEFF_COUNT):
        g_base_filename = os.path.basename(initial_file)
        # g_window_var already set above
    
    # Initialize plot (builds GUI) - NOW SAFE BECAUSE init_plot IS DEFINED
    init_plot()
    
    # Now that GUI is built, refresh window methods combobox
    refresh_available_windows()
    
    # Reset state to initial
    g_manual_coeffs = np.array([])
    g_manual_filtered_data = np.array([])
    g_manual_mode = False
    g_filtered_data = np.array([])
    g_plot_running = False

    # Initial UI update
    update_display_mode()
    update_filter_summary()

    # Start the plot after 500ms to let buffer fill
    g_root.after(500, start_plot)

    print(f"[APP] Plotter ready. Initial file: {g_base_filename}")
    print("[APP] Use the dropdowns on the left to change file, window method, and speed.")
    print("[APP] Data is read in real-time from the selected file.")
    g_root.mainloop()
    
    # Cleanup on exit
    stop_data_stream()

if __name__ == "__main__":
    main()