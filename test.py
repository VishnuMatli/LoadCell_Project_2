import random
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class ModernWeighCellSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sartorius WZB Series - Virtual Weigh Cell Environment")
        self.geometry("1280x820")
        self.minsize(1150, 760)
        
        # 1. Initialize State Variables
        self.machine_running = False
        self.blink_on = False
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.simulated_load = 0.0
        self.target_load = 120.0
        self.noise_seed = 0.0
        self.last_display_value = 0.0
        self.self_test_active = False
        self.adjustment_state = "idle"
        
        # CAS Dynamic Parameter Configuration Registers
        self.active_env_filter = "Stable conditions"
        self.active_app_filter = "Final readout"
        self.active_stability_range = "1 scale interval"
        self.active_zero_range = "2% of max load"
        
        # Core Digital Signal Processing Filter Arrays
        self.filter_history_buffer = []
        self.is_currently_stable = True
        self.previous_weights_history = [0.0] * 5
        
        # Sensor Log File Stream Buffers
        self.file_stream_buffer = []
        self.file_stream_index = 0
        self.is_file_stream_active = False
        self.loaded_file_path = ""
        
        # Calibration Reference Mapping (Based on 535g Sensor Characteristics)
        self.adc_reference_scale = 535.0 / 44347000.0  
        
        # Command Bus Buffers & Transceiver Registers
        self.command_history = []
        self.xbpi_address = 0x00
        
        # 2. Initialize Dynamic UI Tracking Variables
        self.load_var = tk.DoubleVar(value=self.target_load)
        self.status_text = tk.StringVar(value="SYSTEM OFFLINE")
        self.display_text = tk.StringVar(value="------")
        self.raw_text = tk.StringVar(value="Raw Signal : 0.0000 g")
        self.scale_text = tk.StringVar(value="Multiplier : 1.000000")
        self.zero_text = tk.StringVar(value="Zero Ref   : 0.0000 g")
        self.tare_text = tk.StringVar(value="Tare Base  : 0.0000 g")
        self.command_status_text = tk.StringVar(value="BUS PROTOCOL CONSOLE: STANDBY")
        self.stream_status_text = tk.StringVar(value="DATA STREAM: MANUAL MODE")

        # 3. Build UI Architecture
        self._apply_theme_styles()
        self._build_hardware_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_safe_close)

        # High-Fidelity Asynchronous Polling Loops
        self.after(50, self._simulation_engine_tick)
        self.after(350, self._status_blinker_tick)

    def _apply_theme_styles(self):
        """Initializes an advanced industrial dark theme palette configuration."""
        style = ttk.Style(self)
        style.theme_use("clam")
        
        bg_main = "#0B0E14"
        bg_card = "#161B26"
        border_color = "#222A3A"
        text_primary = "#E2E8F0"
        text_muted = "#718096"
        accent_blue = "#00E5FF"
        accent_green = "#00E676"
        accent_red = "#FF3D71"

        self.configure(bg=bg_main)

        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card, relief="flat", borderwidth=0)
        
        style.configure("MainTitle.TLabel", background=bg_main, foreground=text_primary, font=("Segoe UI", 16, "bold"))
        style.configure("SubTitle.TLabel", background=bg_main, foreground=text_muted, font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background=bg_card, foreground=accent_blue, font=("Segoe UI", 11, "bold"))
        style.configure("CardTitleX.TLabel", background=bg_card, foreground=accent_green, font=("Segoe UI", 11, "bold"))
        style.configure("Metric.TLabel", background=bg_card, foreground=text_primary, font=("Consolas", 10, "bold"))
        style.configure("FieldLabel.TLabel", background=bg_card, foreground=text_primary, font=("Segoe UI", 9, "bold"))

        style.configure("Start.TButton", font=("Segoe UI", 9, "bold"), padding=8, background="#00E676", foreground="#0B0E14", borderwidth=0)
        style.map("Start.TButton", background=[("active", "#69F0AE")])

        style.configure("Stop.TButton", font=("Segoe UI", 9, "bold"), padding=8, background=accent_red, foreground=text_primary, borderwidth=0)
        style.map("Stop.TButton", background=[("active", "#FF6B8B")])

        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), padding=6, background="#2A354A", foreground=text_primary, borderwidth=0)
        style.map("Action.TButton", background=[("active", "#374663")])

        style.configure("TEntry", fieldbackground="#0D111A", foreground=text_primary, bordercolor=border_color, padding=6, font=("Consolas", 10))

        style.configure("Treeview", background="#0D111A", fieldbackground="#0D111A", foreground=text_primary, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#1F2937", foreground=text_primary, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#222A3A")], foreground=[("selected", "#00E5FF")])

    def _build_hardware_layout(self):
        root_container = ttk.Frame(self, style="TFrame")
        root_container.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ttk.Frame(root_container, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(header_frame, text="SARTORIUS MULTI-PROTOCOL INTERFACE TESTING SUITE", style="MainTitle.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Dual-Standard physical layer simulation client featuring synchronized RS232-SBI ASCII & xBPI Binary Transceiver Cores.", style="SubTitle.TLabel").pack(anchor="w", pady=(2, 0))

        workspace = ttk.Frame(root_container, style="TFrame")
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=3)  
        workspace.columnconfigure(1, weight=4)  
        workspace.columnconfigure(2, weight=4)  
        workspace.rowconfigure(0, weight=1)

        sidebar_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        sidebar_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._render_cas_sidebar_ui(sidebar_panel)

        left_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        left_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self._render_control_ui(left_panel)

        right_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        right_panel.grid(row=0, column=2, sticky="nsew")
        self._render_telemetry_ui(right_panel)

    def _render_cas_sidebar_ui(self, parent):
        ttk.Label(parent, text="CAS CONFIGURATION SUITE", style="CardTitleX.TLabel").pack(anchor="w", pady=(0, 10))
        
        tree_scroll = ttk.Scrollbar(parent, orient="vertical")
        tree_scroll.pack(side="right", fill="y")
        
        self.cas_tree = ttk.Treeview(parent, yscrollcommand=tree_scroll.set, selectmode="browse")
        self.cas_tree.pack(fill="both", expand=True)
        tree_scroll.config(command=self.cas_tree.yview)
        
        self.cas_tree.heading("#0", text="Device Configuration Parameter List", anchor="w")

        l1_setup = self.cas_tree.insert("", "end", text="1. Active Setup Menu", open=True)
        l1_print = self.cas_tree.insert("", "end", text="2. Active Print Menu")
        l1_device = self.cas_tree.insert("", "end", text="3. Active Device Menu")
        l1_app = self.cas_tree.insert("", "end", text="4. Active Application Menu")

        self.cas_tree.insert(l1_print, "end", text="Print Options Configuration Blocked")
        self.cas_tree.insert(l1_device, "end", text="Device Interface Mapping Blocked")
        self.cas_tree.insert(l1_app, "end", text="Application Control Registers Blocked")

        l2_balance = self.cas_tree.insert(l1_setup, "end", text="1.1 Balance Settings", open=True)

        l3_ambient = self.cas_tree.insert(l2_balance, "end", text="1.1.1 Installation Site / Ambient Conditions")
        l3_filter = self.cas_tree.insert(l2_balance, "end", text="1.1.2 Application Filter")
        l3_stability = self.cas_tree.insert(l2_balance, "end", text="1.1.3 Stability Range")
        l3_delay = self.cas_tree.insert(l2_balance, "end", text="1.1.4 Stability Delay")
        l3_zero = self.cas_tree.insert(l2_balance, "end", text="1.1.11 Zero Range")
        l3_power_zero = self.cas_tree.insert(l2_balance, "end", text="1.1.12 Zero at Power-On")

        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.1 Very stable conditions", values=("env", "Very stable conditions"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.2 Stable conditions", values=("env", "Stable conditions"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.3 Unstable conditions", values=("env", "Unstable conditions"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.4 Very unstable conditions", values=("env", "Very unstable conditions"))

        self.cas_tree.insert(l3_filter, "end", text="1.1.2.1 Final readout", values=("app_filter", "Final readout"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.2 Dosing", values=("app_filter", "Dosing"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.3 Reduced filter", values=("app_filter", "Reduced filter"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.4 Filter off", values=("app_filter", "Filter off"))

        self.cas_tree.insert(l3_stability, "end", text="1.1.3.1 1/4 scale interval", values=("stability", "1/4 scale interval"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.2 1/2 scale interval", values=("stability", "1/2 scale interval"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.3 1 scale interval", values=("stability", "1 scale interval"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.4 2 scale interval", values=("stability", "2 scale interval"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.5 4 scale interval", values=("stability", "4 scale interval"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.6 8 scale interval", values=("stability", "8 scale interval"))

        self.cas_tree.insert(l3_delay, "end", text="1.1.4.1 Very short")
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.2 Short")

        self.cas_tree.insert(l3_zero, "end", text="1.1.11.2 2% of max load", values=("zero_range", "2% of max load"))
        self.cas_tree.insert(l3_zero, "end", text="1.1.11.4 10% of max load", values=("zero_range", "10% of max load"))

        self.cas_tree.insert(l3_power_zero, "end", text="1.1.12.4 10% of max load")
        self.cas_tree.insert(l3_power_zero, "end", text="1.1.12.7 100% of max load")

        self.cas_tree.bind("<<TreeviewSelect>>", self._on_cas_menu_node_click)

    def _on_cas_menu_node_click(self, event):
        selected_node = self.cas_tree.selection()
        if not selected_node:
            return
            
        node_data = self.cas_tree.item(selected_node[0])
        node_values = node_data.get("values", "")
        node_text = node_data.get("text", "")
        
        if node_values:
            param_type, param_value = node_values[0], node_values[1]
            
            if param_type == "env":
                self.active_env_filter = param_value
                self._write_terminal_log(f"[CAS SUITE] Ambient Conditions filter index set to: {param_value}")
            elif param_type == "app_filter":
                self.active_app_filter = param_value
                # Flush existing DSP buffer elements on dynamic parameter reconfigurations
                self.filter_history_buffer.clear()
                self._write_terminal_log(f"[CAS SUITE] Digital Moving Average DSP filter updated to: {param_value}")
            elif param_type == "stability":
                self.active_stability_range = param_value
                self._write_terminal_log(f"[CAS SUITE] Stability confirmation bound set to: {param_value}")
            elif param_type == "zero_range":
                self.active_zero_range = param_value
                self._write_terminal_log(f"[CAS SUITE] Metrological auto-zero tracking limit re-routed: {param_value}")
                
            self._set_command_status(f"UPDATE CODE: {node_text.split()[0]}")

    def _render_telemetry_ui(self, parent):
        ttk.Label(parent, text="METROLOGICAL REAL-TIME READOUT", style="CardTitle.TLabel").pack(anchor="w")

        display_canvas = tk.Frame(parent, bg="#06090E", highlightbackground="#222A3A", highlightthickness=1)
        display_canvas.pack(fill="x", pady=(10, 10))

        unit_overlay = tk.Label(display_canvas, text="NET WT", bg="#06090E", fg="#4A5568", font=("Segoe UI", 9, "bold"))
        unit_overlay.pack(anchor="nw", padx=12, pady=(8, 0))

        self.display_label = tk.Label(
            display_canvas,
            textvariable=self.display_text,
            bg="#06090E",
            fg="#00E5FF",
            font=("Consolas", 34, "bold"),
            anchor="e",
            padx=16,
            pady=8
        )
        self.display_label.pack(fill="x")

        status_bar = ttk.Frame(parent, style="Card.TFrame")
        status_bar.pack(fill="x", pady=(0, 10))

        self.blinker_canvas = tk.Canvas(status_bar, width=24, height=24, bg="#161B26", highlightthickness=0)
        self.blinker_canvas.pack(side="left")
        self.blinker_node = self.blinker_canvas.create_oval(4, 4, 20, 20, fill="#2D3748", outline="#1A202C")

        ttk.Label(status_bar, textvariable=self.status_text, style="Metric.TLabel").pack(side="left", padx=8)

        ttk.Label(parent, text="INSTRUMENTATION PIPELINE CRITICAL REGISTERS", style="CardTitle.TLabel").pack(anchor="w", pady=(6, 4))
        matrix_box = tk.Frame(parent, bg="#0D111A", highlightbackground="#1F2937", highlightthickness=1, padx=12, pady=10)
        matrix_box.pack(fill="x", pady=(0, 14))

        ttk.Label(matrix_box, textvariable=self.raw_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.scale_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.zero_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.tare_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.command_status_text, style="Metric.TLabel", background="#0D111A", foreground="#00E676").pack(anchor="w", pady=2)

        ttk.Label(parent, text="UNIVERSAL SERIAL BUS TRANSPOND MONITOR (HEX & ASCII LOGS)", style="CardTitle.TLabel").pack(anchor="w", pady=(6, 4))
        self.message = tk.Text(parent, height=8, wrap="word", bg="#06090E", fg="#A0AEC0", insertbackground="#E2E8F0", relief="flat", highlightbackground="#222A3A", highlightthickness=1, font=("Consolas", 9))
        self.message.pack(fill="both", expand=True)
        self.message.insert("end", "[CORE] Multi-Standard hardware serial physical driver maps successfully.\n")
        self.message.configure(state="disabled")

    def _render_control_ui(self, parent):
        ttk.Label(parent, text="SYSTEM INITIALIZATION", style="CardTitle.TLabel").pack(anchor="w")
        power_row = ttk.Frame(parent, style="Card.TFrame")
        power_row.pack(fill="x", pady=(8, 14))
        ttk.Button(power_row, text="START WEIGH CELL", style="Start.TButton", command=self.start_machine).pack(side="left")
        ttk.Button(power_row, text="STOP INTEL CIRCUIT", style="Stop.TButton", command=self.stop_machine).pack(side="left", padx=10)

        ttk.Label(parent, text="TRANSDUCER SENSOR DATA INGESTION ENGINE", style="CardTitleX.TLabel").pack(anchor="w")
        ingest_row = ttk.Frame(parent, style="Card.TFrame")
        ingest_row.pack(fill="x", pady=(8, 14))
        
        btn_import = ttk.Button(ingest_row, text="Import Hardware Log (.txt)", style="Action.TButton", command=self._import_sensor_log_file)
        btn_import.pack(side="left")
        
        btn_toggle_mode = ttk.Button(ingest_row, text="Toggle Source Mode", style="Action.TButton", command=self._toggle_stream_source_mode)
        btn_toggle_mode.pack(side="left", padx=10)
        
        self.lbl_stream_status = ttk.Label(ingest_row, textvariable=self.stream_status_text, style="Metric.TLabel", foreground="#00E5FF")
        self.lbl_stream_status.pack(side="left", padx=5)

        ttk.Label(parent, text="SIMULATED RECEPTOR LOAD CONTROL (MANUAL MODE)", style="CardTitle.TLabel").pack(anchor="w")
        slider_row = ttk.Frame(parent, style="Card.TFrame")
        slider_row.pack(fill="x", pady=(8, 14))
        
        self.load_slider = tk.Scale(
            slider_row, from_=0, to=8200, orient="horizontal", resolution=1,
            variable=self.load_var, bg="#161B26", fg="#A0AEC0", troughcolor="#0D111A",
            activebackground="#00E5FF", highlightthickness=0, command=self._on_slider_adjustment, length=320
        )
        self.load_slider.pack(fill="x")
        
        preset_row = ttk.Frame(slider_row, style="Card.TFrame")
        preset_row.pack(fill="x", pady=(4, 0))
        ttk.Button(preset_row, text="Inject 535.0000 g Reference Load", style="Action.TButton", command=lambda: self._inject_preset_load(535.0)).pack(side="left")
        ttk.Button(preset_row, text="Clear Load (0.0000 g)", style="Action.TButton", command=lambda: self._inject_preset_load(0.0)).pack(side="left", padx=10)
        
        self.load_lbl_hint = ttk.Label(slider_row, text="Current Targeted Receptor Mass: 120.0000 g", style="SubTitle.TLabel")
        self.load_lbl_hint.pack(anchor="w", pady=(4, 0))

        ttk.Label(parent, text="MANUAL HARDWARE TRIMMING STATIONS", style="CardTitle.TLabel").pack(anchor="w")
        cal_grid = ttk.Frame(parent, style="Card.TFrame")
        cal_grid.pack(fill="x", pady=(8, 10))
        cal_grid.columnconfigure(0, weight=1)
        cal_grid.columnconfigure(1, weight=1)

        entry_container_1 = ttk.Frame(cal_grid, style="Card.TFrame")
        entry_container_1.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Label(entry_container_1, text="Manual Scaling Factor", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 2))
        self.manual_scale_str = tk.StringVar(value="1.000000")
        self.entry_scale = ttk.Entry(entry_container_1, textvariable=self.manual_scale_str)
        self.entry_scale.pack(fill="x", pady=(0, 4))
        ttk.Button(entry_container_1, text="Apply Scalar Multiplier", style="Action.TButton", command=self.apply_manual_scaling).pack(fill="x")

        entry_container_2 = ttk.Frame(cal_grid, style="Card.TFrame")
        entry_container_2.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(entry_container_2, text="Auto-Calibration Reference (g)", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 2))
        self.auto_ref_str = tk.StringVar(value="500.0")
        self.entry_ref = ttk.Entry(entry_container_2, textvariable=self.auto_ref_str)
        self.entry_ref.pack(fill="x", pady=(0, 4))
        ttk.Button(entry_container_2, text="Compute Dynamic Auto-Scale", style="Action.TButton", command=self.execute_auto_scale).pack(fill="x")

        footer_triggers = ttk.Frame(parent, style="Card.TFrame")
        footer_triggers.pack(fill="x", pady=(6, 14))
        ttk.Button(footer_triggers, text="Zero-Scale Base", style="Action.TButton", command=self.execute_zero_scaling).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(footer_triggers, text="Tare System Offset", style="Action.TButton", command=self.execute_tare).pack(side="left", expand=True, fill="x", padx=3)
        ttk.Button(footer_triggers, text="Reset Local Calibration", style="Action.TButton", command=self.reset_entire_pipeline).pack(side="left", expand=True, fill="x", padx=(3, 0))

        ttk.Label(parent, text="SERIAL REMOTE COMMAND CONSOLE LINK", style="CardTitleX.TLabel").pack(anchor="w")
        command_box = ttk.Frame(parent, style="Card.TFrame")
        command_box.pack(fill="x", pady=(8, 0))
        
        self.protocol_mode = "xBPI"  
        mode_row = ttk.Frame(command_box, style="Card.TFrame")
        mode_row.pack(fill="x", pady=(0, 4))
        self.lbl_mode_indicator = ttk.Label(mode_row, text="Active Protocol Decoder: SARTORIUS xBPI COMPILER MODE", font=("Segoe UI", 9, "bold"), foreground="#00E5FF")
        self.lbl_mode_indicator.pack(side="left")
        
        entry_row = ttk.Frame(command_box, style="Card.TFrame")
        entry_row.pack(fill="x")
        self.command_var = tk.StringVar(value="04 01 09 1E 2C")  
        self.command_entry = ttk.Entry(entry_row, textvariable=self.command_var, font=("Consolas", 10))
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(entry_row, text="Transmit Frame", style="Action.TButton", command=self.send_command).pack(side="right")

    def _write_terminal_log(self, text):
        self.message.configure(state="normal")
        self.message.insert("end", text + "\n")
        self.message.see("end")
        self.message.configure(state="disabled")

    def _set_command_status(self, text):
        self.command_status_text.set(f"BUS DATA MATRIX STATUS: {text.upper()}")

    def _on_slider_adjustment(self, val):
        try:
            self.target_load = float(val)
        except ValueError:
            self.target_load = 0.0
        self.load_lbl_hint.configure(text=f"Current Targeted Receptor Mass: {self.target_load:,.4f} g")

    def _inject_preset_load(self, target_mass):
        self.is_file_stream_active = False
        self.stream_status_text.set("DATA STREAM: MANUAL MODE")
        self.load_var.set(target_mass)
        self._on_slider_adjustment(target_mass)
        self._write_terminal_log(f"[HARDWARE] Reference mass override: {target_mass:,.4f} g tracked onto pan receptor.")

    def _generate_live_signal(self):
        """Generates raw transducer input metrics with ambient noise configurations."""
        if self.is_file_stream_active and self.file_stream_buffer:
            raw_adc = self.file_stream_buffer[self.file_stream_index]
            self.file_stream_index = (self.file_stream_index + 1) % len(self.file_stream_buffer)
            source_weight = raw_adc * self.adc_reference_scale
        else:
            source_weight = self.simulated_load

        # 1. Map CAS Ambient Conditions Noise Limits (1.1.1)
        if "Very stable" in self.active_env_filter:
            noise_bound = 0.002
        elif "Very unstable" in self.active_env_filter:
            noise_bound = 0.165
        elif "Unstable" in self.active_env_filter:
            noise_bound = 0.065
        else:
            noise_bound = 0.018 # Standard Default Baseline Configuration
            
        environmental_noise = random.uniform(-noise_bound, noise_bound)
        vibration_drift = 0.0008 * self.noise_seed
        self.noise_seed = (self.noise_seed + 0.5) % 500.0
        
        raw_signal_output = source_weight + environmental_noise + vibration_drift
        
        # 2. Map CAS Application Moving Average Filter Window Sizes (1.1.2)
        if "Final readout" in self.active_app_filter:
            filter_window_size = 18   # Maximum dampening window
        elif "Reduced filter" in self.active_app_filter:
            filter_window_size = 6    # Light rapid averaging window
        elif "Filter off" in self.active_app_filter:
            filter_window_size = 1    # Directly pass real-time updates
        else:
            filter_window_size = 10   # Standard Dosing/Stabilization filter length
            
        self.filter_history_buffer.append(raw_signal_output)
        if len(self.filter_history_buffer) > filter_window_size:
            self.filter_history_buffer.pop(0)
            
        # Return calculated mathematical sliding mean 
        return sum(self.filter_history_buffer) / len(self.filter_history_buffer)

    def _process_calibrated_weight(self, source_signal):
        return ((source_signal - self.zero_reference) * self.scale_factor) - self.tare_offset

    def _evaluate_measurement_stability(self, current_calculated_weight):
        """Evaluates noise variance across history array bounds to determine metrological stability."""
        self.previous_weights_history.append(current_calculated_weight)
        if len(self.previous_weights_history) > 5:
            self.previous_weights_history.pop(0)
            
        # Determine internal delta span variance boundaries
        max_delta = max(self.previous_weights_history) - min(self.previous_weights_history)
        
        # 3. Map CAS Stability scale thresholds configurations (1.1.3)
        if "1/4 scale" in self.active_stability_range:
            allowed_threshold = 0.0025
        elif "4 scale" in self.active_stability_range:
            allowed_threshold = 0.0400
        elif "8 scale" in self.active_stability_range:
            allowed_threshold = 0.0800
        else:
            allowed_threshold = 0.0100 # Default matches standard 1 scale interval
            
        self.is_currently_stable = max_delta <= allowed_threshold

    def start_machine(self):
        if self.machine_running:
            return
        self.machine_running = True
        self.status_text.set("ONLINE | METROLOGY RUNNING")
        self._write_terminal_log("[SYSTEM] Main core processor cycle initiated.")

    def stop_machine(self):
        if not self.machine_running:
            return
        self.machine_running = False
        self.blink_on = False
        self.status_text.set("SYSTEM OFFLINE")
        self.blinker_canvas.itemconfig(self.blinker_node, fill="#2D3748", outline="#1A202C")
        self.display_text.set("OFFLINE")
        self._write_terminal_log("[SYSTEM] Main core processor cycle stopped.")

    def apply_manual_scaling(self):
        try:
            factor = float(self.manual_scale_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid numerical entry matrix.")
            return
        if factor <= 0:
            messagebox.showerror("Range Fault", "System calibration scaling must execute above absolute zero baseline limit.")
            return
        self.scale_factor = factor
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._write_terminal_log(f"[CAL] Local calibration manual scale matrix set to factor: {self.scale_factor:.6f}")

    def execute_zero_scaling(self):
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        
        # 4. Map CAS Zero-Tracking safety bounds constraints (1.1.11)
        max_allowed_zero_drift = 164.0 if "10%" in self.active_zero_range else 32.8 # 2% or 10% of maximum limits
        if abs(current_raw) > max_allowed_zero_drift:
            messagebox.showerror("Zero Error", f"Cannot establish static zero base. Current signal exceeds configured tracking boundary rules ({self.active_zero_range}).")
            self._write_terminal_log("[SYSTEM BASE ERR] Static zero calculation out of range bounds parameters.")
            return
            
        self.zero_reference = current_raw
        self.zero_text.set(f"Zero Ref   : {self.zero_reference:,.4f} g")
        self._write_terminal_log(f"[CAL] Local hardware static zero reference stored at: {self.zero_reference:,.4f} g")

    def execute_tare(self):
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.tare_offset = self._process_calibrated_weight(current_raw)
        self.tare_text.set(f"Tare Base  : {self.tare_offset:,.4f} g")
        self._write_terminal_log(f"[CAL] Tare baseline compensation register configuration latched: {self.tare_offset:,.4f} g")

    def execute_auto_scale(self):
        try:
            reference_weight = float(self.auto_ref_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Calibration standard point syntax failure.")
            return
        if reference_weight <= 0:
            messagebox.showerror("Range Fault", "Dynamic linear calibration checks require metric values above zero.")
            return

        sample_raw = self._generate_live_signal() if self.machine_running else max(self.simulated_load, 0.001)
        delta_span = sample_raw - self.zero_reference
        if abs(delta_span) < 1e-5:
            messagebox.showerror("Algorithmic Fault", "Sensor voltage differential output profile span is too narrow.")
            return

        self.scale_factor = reference_weight / delta_span
        self.manual_scale_str.set(f"{self.scale_factor:.6f}")
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._write_terminal_log(f"[CAL] Automated adjustment linear scaling complete using standard target: {reference_weight:.4f} g")

    def reset_entire_pipeline(self):
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Multiplier : 1.000000")
        self.zero_text.set("Zero Ref   : 0.0000 g")
        self.tare_text.set("Tare Base  : 0.0000 g")
        self._write_terminal_log("[CAL] Dynamic calibration pipelines flushed. Memory parameters reset to raw sensor defaults.")

    def _import_sensor_log_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path:
            return

        try:
            temp_buffer = []
            with open(file_path, "r") as f:
                for line in f:
                    cleaned = line.strip()
                    if cleaned.startswith("ADC:"):
                        try:
                            adc_val = float(cleaned.split(":")[1])
                            temp_buffer.append(adc_val)
                        except (IndexError, ValueError):
                            continue
            
            if not temp_buffer:
                messagebox.showerror("Parse Fault", "No recognizable 'ADC:xxxxxxxx' patterns found inside raw file context.")
                return

            self.file_stream_buffer = temp_buffer
            self.file_stream_index = 0
            self.loaded_file_path = os.path.basename(file_path)
            self.is_file_stream_active = True
            
            self.stream_status_text.set(f"DATA STREAM: {self.loaded_file_path}")
            self._write_terminal_log(f"[INGEST] Cached {len(self.file_stream_buffer)} signal elements from file standard: {self.loaded_file_path}")
            
        except Exception as e:
            messagebox.showerror("I/O System Error", f"Failed to ingest raw stream data: {str(e)}")

    def _toggle_stream_source_mode(self):
        if not self.file_stream_buffer:
            messagebox.showwarning("Pipeline Interlock", "Load a verified hardware log file before changing source pipeline tracking methods.")
            return

        self.is_file_stream_active = not self.is_file_stream_active
        if self.is_file_stream_active:
            self.stream_status_text.set(f"DATA STREAM: {self.loaded_file_path}")
            self._write_terminal_log("[SYSTEM] Re-routing sensor tracks to text frame stream log vector arrays.")
        else:
            self.stream_status_text.set("DATA STREAM: MANUAL MODE")
            self._write_terminal_log("[SYSTEM] Reverting transducer metrics back to manual load tracking lines.")

    def send_command(self):
        raw_input = self.command_var.get().strip()
        if not raw_input:
            self._set_command_status("EMPTY TELEMETRY FRAME")
            return

        if raw_input.upper().startswith("ESC") or len(raw_input.split()) == 0 or not all(c in "0123456789ABCDEFabcdef " for c in raw_input):
            self.protocol_mode = "RS232/SBI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: LEGACY RS232-SBI MODE (ASCII STRINGS)", foreground="#FF3D71")
            normalized_ascii = raw_input.upper()
            tx_frame = self._process_legacy_rs232_ascii(normalized_ascii)
            self.command_history.append((raw_input, tx_frame))
            self._write_terminal_log(f"[RS232 RX] ASCII -> '{raw_input}' | [TX Response] -> {tx_frame}")
            self._set_command_status(tx_frame)
        else:
            self.protocol_mode = "xBPI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: SARTORIUS xBPI COMPILER MODE (BINARY)", foreground="#00E676")
            try:
                byte_array = bytes.fromhex(raw_input)
                tx_bytes = self._process_binary_xbpi_frame(byte_array)
                tx_hex_string = " ".join(f"{b:02X}" for b in tx_bytes)
                self.command_history.append((raw_input, tx_hex_string))
                self._write_terminal_log(f"[xBPI RX] Binary Frame -> {raw_input} | [TX Response] -> {tx_hex_string}")
                self._set_command_status(f"TX SUCCESS")
            except ValueError:
                self._set_command_status("FRAME STRUCT ERROR")

    def _process_binary_xbpi_frame(self, data: bytes) -> bytes:
        if len(data) < 3: return bytes([0x03, 0x41, 0x95])  
        if len(data) != data[0] + 1: return bytes([0x03, 0x41, 0x95])  
        if sum(data[:-1]) % 256 != data[-1]: return bytes([0x03, 0x41, 0x92])  

        function_number = data[3] if len(data) > 3 else 0x00
        response_frame = bytearray()
        
        if function_number == 0x1E:   
            response_payload = bytes([0x48, 0x42, 0x14, 0x8F, 0x5C, 0x28, 0x34, 0x43])
            response_frame.extend(response_payload)
            self.adjustment_state = "idle"
        elif function_number == 0x16: 
            self.execute_tare()
            response_frame.extend(bytes([0x00]))  
        elif function_number == 0x18: 
            self.execute_zero_scaling()
            response_frame.extend(bytes([0x00]))  
        elif function_number == 0x01: 
            response_frame.extend(bytes([0x45, 0x12, 0x34, 0x56, 0x78, 0x90]))
        elif function_number == 0x02: 
            response_frame.extend(bytes([0x49]) + "IS64FEG         ".encode('ascii'))
        elif function_number == 0x28: 
            self.adjustment_state = "external adjustment"
            self.execute_auto_scale()
            response_frame.extend(bytes([0x00]))  
        elif function_number == 0x29: 
            self.adjustment_state = "idle"
            response_frame.extend(bytes([0x00]))  
        else:
            response_frame.extend(bytes([0x01, 0x01]))  

        final_tx_packet = bytearray([len(response_frame) + 2, 0x41]) + response_frame
        final_tx_packet.append(sum(final_tx_packet) % 256)
        return bytes(final_tx_packet)

    def _process_legacy_rs232_ascii(self, cmd: str) -> str:
        if cmd in {"ESC T", "ESC TARE", "TARE"}:
            self.execute_tare()
            return "TARE/ZERO ACK"
        elif cmd in {"ESC V", "ESC ZERO", "ZERO"}:
            self.execute_zero_scaling()
            return "ZERO ACK"
        elif cmd in {"ESC W", "ESC S1_"}:
            self.adjustment_state = "external adjustment"
            self.execute_auto_scale()
            return "EXT CAL RUNNING"
        elif cmd in {"ESC Z", "ESC X0_"}:
            self.adjustment_state = "internal calibration"
            if not self.machine_running: self.start_machine()
            self.execute_tare()
            self.scale_factor = 1.0
            return "INT CAL RUNNING"
        elif cmd == "ESC S":
            self.reset_entire_pipeline()
            return "DIAGNOSTIC COMPLETE"
        elif cmd == "ESC P":
            return f"WT + {self.last_display_value:,.4f} g"
        else:
            return f"ERR: COMMAND UNRECOGNIZED [{cmd}]"

    def _simulation_engine_tick(self):
        if self.machine_running:
            if not self.is_file_stream_active:
                self.simulated_load += (self.target_load - self.simulated_load) * 0.12
            
            raw_signal = self._generate_live_signal()
            transformed_net_weight = self._process_calibrated_weight(raw_signal)
            self.last_display_value = transformed_net_weight
            
            # Continuously monitor stability markers
            self._evaluate_measurement_stability(transformed_net_weight)
            stability_flag = " " if self.is_currently_stable else " [UNSTABLE]"
            
            self.display_text.set(f"{transformed_net_weight:,.4f} g{stability_flag}")
            self.raw_text.set(f"Raw Signal : {raw_signal:,.4f} g")
            
            if self.adjustment_state == "external adjustment":
                self.status_text.set("CAL.EXT" if not self.blink_on else "CALRUN")
            elif self.adjustment_state == "internal calibration":
                self.status_text.set("CAL.INT" if not self.blink_on else "CALRUN")
            else:
                self.status_text.set("ONLINE | METROLOGY RUNNING" if not self.blink_on else "ONLINE | DATA BUS ACTIVE")
        else:
            self.display_text.set("OFFLINE")
            if self.is_file_stream_active and self.file_stream_buffer:
                self.raw_text.set(f"Raw Signal : [STREAM PAUSED] {self.file_stream_buffer[self.file_stream_index] * self.adc_reference_scale:,.4f} g")
            else:
                self.raw_text.set(f"Raw Signal : {self.simulated_load:,.4f} g")

        self.after(50, self._simulation_engine_tick)

    def _status_blinker_tick(self):
        if self.machine_running:
            self.blink_on = not self.blink_on
            fill_color = "#00E676" if self.blink_on else "#004D2C"
            self.blinker_canvas.itemconfig(self.blinker_node, fill=fill_color, outline="#B9F6CA" if self.blink_on else "#002314")
        else:
            self.blinker_canvas.itemconfig(self.blinker_node, fill="#2D3748", outline="#1A202C")
            self.status_text.set("SYSTEM OFFLINE")
        self.after(350, self._status_blinker_tick)

    def _on_safe_close(self):
        self.machine_running = False
        self.destroy()


if __name__ == "__main__":
    app = ModernWeighCellSimulator()
    app.mainloop()