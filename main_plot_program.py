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


def get_frame_step(interval_ms):
    # Larger step for smaller interval makes speed differences clearly visible.
    if interval_ms <= 5:
        return 10
    if interval_ms <= 10:
        return 5
    if interval_ms <= 20:
        return 2
    return 1

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
g_raw_data = np.array([])
g_reference_filtered_data = np.array([])
g_filtered_data = np.array([])
g_manual_filtered_data = np.array([])
g_manual_coeffs = np.array([])
g_manual_mode = False
g_animation = None
g_interval_ms = DEFAULT_INTERVAL_MS
g_coeffs_text_widget = None

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


def available_windows_for_file(base_filename):
    windows = []
    for window_method in WINDOW_METHODS:
        expected_name = f"filtered_{window_method}_{base_filename}"
        candidates = [
            os.path.join("output", window_method, expected_name),
            expected_name,
            os.path.join("..", "output", window_method, expected_name),
            os.path.join("..", expected_name),
        ]
        if any(os.path.exists(path) for path in candidates):
            windows.append(window_method)
    return windows


def choose_default_window(base_filename, preferred_window=None):
    windows = available_windows_for_file(base_filename)
    if preferred_window in windows:
        return preferred_window, windows
    if windows:
        return windows[0], windows
    return (preferred_window if preferred_window in WINDOW_METHODS else WINDOW_METHODS[0], windows)


def load_raw_data(base_filename):
    candidates = [
        os.path.join("adc_data", base_filename),
        os.path.join("client_files", base_filename),
        base_filename,
        os.path.join("..", "adc_data", base_filename),
        os.path.join("..", "client_files", base_filename),
        os.path.join("..", base_filename),
    ]

    for path in candidates:
        if os.path.exists(path):
            adc_values = []
            with open(path, "r") as f:
                for line in f:
                    m = re.search(r"-?\d+", line)
                    if m:
                        try:
                            adc_values.append(int(m.group(0)))
                        except ValueError:
                            continue
            if adc_values:
                print(f"[APP] Loaded raw ADC file: {path}")
                return normalize_adc_to_weights(adc_values)

    raise FileNotFoundError(f"Raw ADC data not found for base file: {base_filename}")


def load_filtered_data(base_filename, window_method):
    expected_name = f"filtered_{window_method}_{base_filename}"
    candidates = [
        os.path.join("output", window_method, expected_name),
        expected_name,
        os.path.join("..", "output", window_method, expected_name),
        os.path.join("..", expected_name),
    ]

    for path in candidates:
        if os.path.exists(path):
            vals = []
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        vals.append(float(line))
                    except ValueError:
                        continue
            if vals:
                print(f"[APP] Loaded filtered file: {path}")
                return np.array(vals, dtype=float)

    raise FileNotFoundError(
        f"Filtered output not found for window '{window_method}' and file '{base_filename}'. "
        f"Expected: output/{window_method}/{expected_name}"
    )


def create_plot_limits(series, start_index, end_index):
    visible = series[int(start_index): int(end_index)]
    if visible.size == 0:
        return None
    y_min = float(np.nanmin(visible))
    y_max = float(np.nanmax(visible))
    span = y_max - y_min
    pad = max(span * 0.12, 0.1)
    return y_min - pad, y_max + pad


def calculate_bandwidth(series):
    if series is None or len(series) == 0:
        return 0.0
    return float(np.nanmax(series) - np.nanmin(series))


def parse_manual_coefficients(text):
    tokens = re.split(r"[\s,;]+", text.strip())
    coeffs = []
    for token in tokens:
        if not token:
            continue
        coeffs.append(float(token))
    if not coeffs:
        raise ValueError("Please enter at least one coefficient.")
    return np.array(coeffs, dtype=float)


def apply_manual_fir_filter(raw_series, coeffs):
    if raw_series is None or len(raw_series) == 0:
        return np.array([], dtype=float)
    if coeffs is None or len(coeffs) == 0:
        return np.zeros_like(raw_series, dtype=float)
    filtered = np.convolve(np.asarray(raw_series, dtype=float), np.asarray(coeffs, dtype=float), mode="full")
    return filtered[: len(raw_series)]


def has_manual_output():
    return g_manual_mode and g_manual_coeffs.size > 0 and g_manual_filtered_data.size > 0


def current_filtered_series():
    return g_manual_filtered_data if has_manual_output() else g_reference_filtered_data


def get_difference_metrics():
    if not has_manual_output() or g_reference_filtered_data.size == 0:
        return None
    compare_len = min(len(g_manual_filtered_data), len(g_reference_filtered_data))
    if compare_len <= 0:
        return None
    diff = g_manual_filtered_data[:compare_len] - g_reference_filtered_data[:compare_len]
    return {
        "max_abs": float(np.max(np.abs(diff))),
        "mean_abs": float(np.mean(np.abs(diff))),
        "rmse": float(np.sqrt(np.mean(diff ** 2))),
    }


def format_status_text(prefix=None):
    base = f"File: {g_base_filename} | Window: {g_selected_window} | Speed: {g_interval_ms} ms"
    metrics = get_difference_metrics()
    if metrics is not None:
        base += (
            f" | Manual coeffs ON | Max diff: {metrics['max_abs']:.4f}"
            f" | Mean diff: {metrics['mean_abs']:.4f} | RMSE: {metrics['rmse']:.4f}"
        )
    if prefix:
        return f"{prefix} | {base}"
    return base


def update_status_text(prefix=None):
    if g_status_var is not None:
        g_status_var.set(format_status_text(prefix))


def update_display_mode():
    if axes is None:
        return

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
        manual_filtered_line.set_label("Manual FIR Output")
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
    global g_manual_filtered_data, g_filtered_data, g_manual_mode

    if g_manual_coeffs.size == 0:
        g_manual_filtered_data = np.array([], dtype=float)
        g_manual_mode = False
        g_filtered_data = g_reference_filtered_data
        return

    g_manual_filtered_data = apply_manual_fir_filter(g_raw_data, g_manual_coeffs)
    g_filtered_data = g_manual_filtered_data
    g_manual_mode = True


def update_filter_summary():
    raw_bandwidth = calculate_bandwidth(g_raw_data)
    reference_bandwidth = calculate_bandwidth(g_reference_filtered_data)
    display_bandwidth = calculate_bandwidth(current_filtered_series())
    if g_bandwidth_var is not None:
        if has_manual_output():
            g_bandwidth_var.set(
                f"Raw bandwidth: {raw_bandwidth:.2f}    |    Reference: {reference_bandwidth:.2f}    |    Manual: {display_bandwidth:.2f}"
            )
        else:
            g_bandwidth_var.set(
                f"Raw bandwidth: {raw_bandwidth:.2f}    |    Filtered bandwidth: {display_bandwidth:.2f}"
            )
    update_status_text()


def update_bandwidth_labels():
    if g_bandwidth_var is None:
        return
    raw_bandwidth = calculate_bandwidth(g_raw_data)
    filtered_bandwidth = calculate_bandwidth(g_filtered_data)
    g_bandwidth_var.set(
        f"Raw bandwidth: {raw_bandwidth:.2f}    |    Filtered bandwidth: {filtered_bandwidth:.2f}"
    )


def refresh_available_windows():
    global g_available_windows
    g_available_windows = available_windows_for_file(g_base_filename)
    if g_window_var is not None:
        current = g_window_var.get()
        if current not in g_available_windows:
            next_window, _ = choose_default_window(g_base_filename, current)
            g_window_var.set(next_window)
            globals()["g_selected_window"] = next_window


def load_selected_data(base_filename=None, window_method=None):
    global g_raw_data, g_reference_filtered_data, g_filtered_data, g_base_filename, g_selected_window, g_available_windows

    if base_filename is not None:
        g_base_filename = os.path.basename(base_filename)
    if window_method is not None:
        g_selected_window = window_method

    g_raw_data = load_raw_data(g_base_filename)
    selected_window, g_available_windows = choose_default_window(g_base_filename, g_selected_window)
    g_selected_window = selected_window

    try:
        g_reference_filtered_data = load_filtered_data(g_base_filename, g_selected_window)
    except Exception as exc:
        print(f"[APP] {exc}")
        g_reference_filtered_data = np.zeros_like(g_raw_data)

    if has_manual_output():
        recompute_manual_output()
    else:
        g_filtered_data = g_reference_filtered_data


def update_plot_titles():
    base = os.path.basename(g_base_filename)
    if axes is not None:
        axes[0].set_title(f"Raw ADC Data - {base}")
        if has_manual_output():
            axes[1].set_title(f"Manual FIR Filtered Data vs Reference - {base}")
        else:
            axes[1].set_title(f"FIR Filtered Data ({g_selected_window}) - {base}")


def set_visible_limits(frame):
    if len(g_raw_data) == 0 or len(g_filtered_data) == 0:
        return

    if len(g_raw_data) <= PLOT_WINDOW_SIZE:
        x_min = 0
        x_max = max(len(g_raw_data), len(g_filtered_data), PLOT_WINDOW_SIZE)
    else:
        x_min = max(0, frame + 1 - PLOT_WINDOW_SIZE)
        x_max = min(x_min + PLOT_WINDOW_SIZE, min(len(g_raw_data), len(g_filtered_data)))

    axes[0].set_xlim(x_min, x_max)
    axes[1].set_xlim(x_min, x_max)

    raw_limits = create_plot_limits(g_raw_data, x_min, x_max)
    filtered_limits = create_plot_limits(g_filtered_data, x_min, x_max)

    if raw_limits is not None:
        axes[0].set_ylim(*raw_limits)
    if filtered_limits is not None:
        axes[1].set_ylim(*filtered_limits)


def init_plot():
    global fig, axes, raw_line, filtered_line, manual_filtered_line, g_canvas, control_frame, stats_frame
    global sidebar_canvas, sidebar_scrollbar, sidebar_inner, g_coeffs_text_widget

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
    axes[0].legend(loc="upper right", frameon=True, facecolor="white")

    axes[1].set_title("FIR Filtered Data", fontsize=12, weight="bold", color="#243043")
    axes[1].set_xlabel("Sample Index", color="#243043")
    axes[1].set_ylabel("Weight", color="#243043")
    axes[1].legend(loc="upper right", frameon=True, facecolor="white")

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

    section_label("Manual FIR Coefficients").pack(fill=tk.X, padx=14)
    coeff_help = tk.Label(
        sidebar_inner,
        text="Enter coefficients separated by spaces, commas, or new lines.",
        bg="#1f2d3d",
        fg="#8aa0bf",
        wraplength=230,
        justify="left",
        pady=4,
    )
    coeff_help.pack(fill=tk.X, padx=14)

    coeffs_text = tk.Text(
        sidebar_inner,
        height=5,
        width=28,
        bg="#f7fbff",
        fg="#243043",
        insertbackground="#243043",
        relief="flat",
        padx=8,
        pady=8,
        wrap="word",
    )
    coeffs_text.pack(fill=tk.X, padx=14, pady=(0, 10))
    coeffs_text.insert("1.0", "0.25, 0.25, 0.25, 0.25")
    g_coeffs_text_widget = coeffs_text

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


def update_frame(frame):
    x = np.arange(frame + 1)
    y_raw = g_raw_data[: frame + 1]
    y_ref = g_reference_filtered_data[: frame + 1]
    y_filt = current_filtered_series()[: frame + 1]

    raw_line.set_data(x, y_raw)
    filtered_line.set_data(x, y_ref)
    manual_filtered_line.set_data(x, y_filt)

    set_visible_limits(frame)

    return raw_line, filtered_line, manual_filtered_line


def restart_animation():
    global g_animation
    if g_animation and g_animation.event_source:
        g_animation.event_source.stop()

    n = min(len(g_raw_data), len(current_filtered_series()))
    if n <= 0:
        print("[APP] No data to animate")
        return

    frame_step = get_frame_step(g_interval_ms)
    frames = range(0, n, frame_step)

    g_animation = FuncAnimation(
        fig,
        update_frame,
        frames=frames,
        interval=g_interval_ms,
        blit=False,
        repeat=False,
    )
    if g_canvas is not None:
        g_canvas.draw_idle()


def apply_manual_coeffs_from_controls():
    global g_manual_coeffs

    if g_coeffs_text_widget is None:
        return

    coeff_text = g_coeffs_text_widget.get("1.0", tk.END)
    try:
        g_manual_coeffs = parse_manual_coefficients(coeff_text)
    except Exception as exc:
        update_status_text(f"Invalid manual coefficients: {exc}")
        return

    recompute_manual_output()
    update_plot_titles()
    update_display_mode()
    update_filter_summary()
    restart_animation()


def clear_manual_coeffs():
    global g_manual_coeffs, g_manual_filtered_data, g_filtered_data, g_manual_mode

    g_manual_coeffs = np.array([])
    g_manual_filtered_data = np.array([])
    g_filtered_data = g_reference_filtered_data
    g_manual_mode = False
    update_plot_titles()
    update_display_mode()
    update_filter_summary()
    restart_animation()


def reload_filtered_and_restart():
    global g_reference_filtered_data, g_filtered_data

    try:
        g_reference_filtered_data = load_filtered_data(g_base_filename, g_selected_window)
    except Exception as e:
        print(f"[APP] {e}")
        # Keep existing data if available; otherwise zero array
        if g_reference_filtered_data.size == 0:
            g_reference_filtered_data = np.zeros_like(g_raw_data)

    if has_manual_output():
        recompute_manual_output()
    else:
        g_filtered_data = g_reference_filtered_data

    update_plot_titles()
    if g_window_var is not None and g_window_var.get() != g_selected_window:
        g_window_var.set(g_selected_window)
    update_display_mode()
    update_filter_summary()
    restart_animation()


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
    selected_file = g_file_var.get().strip()
    if not selected_file:
        return
    load_selected_data(selected_file, g_window_var.get().strip() if g_window_var else None)
    refresh_available_windows()
    if g_window_var is not None:
        g_window_var.set(g_selected_window)
    reload_filtered_and_restart()


def on_window_selected(_event):
    selected_window = g_window_var.get().strip()
    if selected_window:
        globals()["g_selected_window"] = selected_window
        reload_filtered_and_restart()


def on_speed_selected(_event):
    selected_speed = g_speed_var.get().strip()
    if selected_speed.endswith("ms"):
        globals()["g_interval_ms"] = int(selected_speed[:-2])
        if g_animation and g_animation.event_source:
            g_animation.event_source.interval = g_interval_ms
        update_status_text()
        restart_animation()


def main():
    global g_root, g_status_var, g_bandwidth_var, g_file_var, g_window_var, g_speed_var, g_available_files
    global g_reference_filtered_data, g_filtered_data, g_manual_filtered_data, g_manual_coeffs, g_manual_mode

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
    g_root.title("ADC Plotter")
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
    g_window_var = tk.StringVar(value=g_selected_window)
    g_speed_var = tk.StringVar(value=f"{g_interval_ms}ms")

    load_selected_data(initial_file, g_selected_window)
    refresh_available_windows()
    g_window_var.set(g_selected_window)

    g_manual_coeffs = np.array([])
    g_manual_filtered_data = np.array([])
    g_manual_mode = False
    g_filtered_data = g_reference_filtered_data

    init_plot()
    reload_filtered_and_restart()
    update_bandwidth_labels()

    print(f"[APP] Plotter ready. Initial file: {g_base_filename}")
    print("[APP] Use the dropdowns on the left to change file, window method, and speed.")
    g_root.mainloop()


if __name__ == "__main__":
    main()
