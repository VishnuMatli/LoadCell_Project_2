import random
import tkinter as tk
from tkinter import ttk, messagebox


class ModernWeighCellSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sartorius WZB Series - Virtual Weigh Cell Environment")
        self.geometry("1080x720")
        self.minsize(1020, 660)
        
        # Core Simulation State Variables
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
        self.command_history = []

        # String Variables for Dynamic UI Tracking
        self.status_text = tk.StringVar(value="SYSTEM OFFLINE")
        self.display_text = tk.StringVar(value="------")
        self.raw_text = tk.StringVar(value="Raw Signal : 0.0000 g")
        self.scale_text = tk.StringVar(value="Multiplier : 1.000000")
        self.zero_text = tk.StringVar(value="Zero Ref   : 0.0000 g")
        self.tare_text = tk.StringVar(value="Tare Base  : 0.0000 g")
        self.command_status_text = tk.StringVar(value="RS232: IDLE")

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
        accent_red = "#FF3D71"

        self.configure(bg=bg_main)

        # Global Structural Framework
        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card, relief="flat", borderwidth=0)
        
        style.configure("MainTitle.TLabel", background=bg_main, foreground=text_primary, font=("Segoe UI", 18, "bold"))
        style.configure("SubTitle.TLabel", background=bg_main, foreground=text_muted, font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=bg_card, foreground=accent_blue, font=("Segoe UI", 11, "bold"))
        style.configure("Metric.TLabel", background=bg_card, foreground=text_primary, font=("Consolas", 10, "bold"))
        style.configure("FieldLabel.TLabel", background=bg_card, foreground=text_primary, font=("Segoe UI", 9, "bold"))

        # Hardware Control Action Triggers
        style.configure("Start.TButton", font=("Segoe UI", 9, "bold"), padding=8, background="#00E676", foreground="#0B0E14", borderwidth=0)
        style.map("Start.TButton", background=[("active", "#69F0AE")])

        style.configure("Stop.TButton", font=("Segoe UI", 9, "bold"), padding=8, background=accent_red, foreground=text_primary, borderwidth=0)
        style.map("Stop.TButton", background=[("active", "#FF6B8B")])

        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), padding=6, background="#2A354A", foreground=text_primary, borderwidth=0)
        style.map("Action.TButton", background=[("active", "#374663")])

        # Input Field Geometry
        style.configure("TEntry", fieldbackground="#0D111A", foreground=text_primary, bordercolor=border_color, padding=6, font=("Consolas", 10))

    def _build_hardware_layout(self):
        root_container = ttk.Frame(self, style="TFrame")
        root_container.pack(fill="both", expand=True, padx=24, pady=24)

        # Workspace Header Module
        header_frame = ttk.Frame(root_container, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(header_frame, text="SARTORIUS WZB INTERFACE EMULATOR", style="MainTitle.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="High-precision digital weigh cell instrumentation client and terminal link dashboard.", style="SubTitle.TLabel").pack(anchor="w", pady=(2, 0))

        # Main Interface Layout Splitting
        workspace = ttk.Frame(root_container, style="TFrame")
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=4)  # Left Parameter Console Panel
        workspace.columnconfigure(1, weight=3)  # Right Telemetry HUD & Console
        workspace.rowconfigure(0, weight=1)

        left_panel = ttk.Frame(workspace, style="Card.TFrame", padding=20)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        right_panel = ttk.Frame(workspace, style="Card.TFrame", padding=20)
        right_panel.grid(row=0, column=1, sticky="nsew")

        self._render_telemetry_ui(right_panel)
        self._render_control_ui(left_panel)

    def _render_telemetry_ui(self, parent):
        ttk.Label(parent, text="INSTRUMENT METROLOGY HUD", style="CardTitle.TLabel").pack(anchor="w")

        # Core Transflective LCD Emulation Grid
        display_canvas = tk.Frame(parent, bg="#06090E", highlightbackground="#222A3A", highlightthickness=1)
        display_canvas.pack(fill="x", pady=(14, 12))

        unit_overlay = tk.Label(display_canvas, text="NET WT", bg="#06090E", fg="#4A5568", font=("Segoe UI", 9, "bold"))
        unit_overlay.pack(anchor="nw", padx=14, pady=(10, 0))

        self.display_label = tk.Label(
            display_canvas,
            textvariable=self.display_text,
            bg="#06090E",
            fg="#00E5FF",
            font=("Consolas", 40, "bold"),
            anchor="e",
            padx=20,
            pady=10
        )
        self.display_label.pack(fill="x")

        # Dynamic System Pulse Beacon Strip
        status_bar = ttk.Frame(parent, style="Card.TFrame")
        status_bar.pack(fill="x", pady=(0, 14))

        self.blinker_canvas = tk.Canvas(status_bar, width=28, height=28, bg="#161B26", highlightthickness=0)
        self.blinker_canvas.pack(side="left")
        self.blinker_node = self.blinker_canvas.create_oval(6, 6, 22, 22, fill="#2D3748", outline="#1A202C")

        ttk.Label(status_bar, textvariable=self.status_text, style="Metric.TLabel").pack(side="left", padx=10)

        # Real-Time Core Bus Telemetry Matrix
        ttk.Label(parent, text="REAL-TIME TELEMETRY MATRIX", style="CardTitle.TLabel").pack(anchor="w", pady=(8, 6))
        matrix_box = tk.Frame(parent, bg="#0D111A", highlightbackground="#1F2937", highlightthickness=1, padx=14, pady=12)
        matrix_box.pack(fill="x")

        ttk.Label(matrix_box, textvariable=self.raw_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=3)
        ttk.Label(matrix_box, textvariable=self.scale_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=3)
        ttk.Label(matrix_box, textvariable=self.zero_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=3)
        ttk.Label(matrix_box, textvariable=self.tare_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=3)
        ttk.Label(matrix_box, textvariable=self.command_status_text, style="Metric.TLabel", background="#0D111A", foreground="#E2E8F0").pack(anchor="w", pady=3)

        # Integrated RS232 Serial Trceiver Logs Window
        ttk.Label(parent, text="SERIAL TRANSCEIVER LINE MONITOR", style="CardTitle.TLabel").pack(anchor="w", pady=(16, 6))
        self.message = tk.Text(parent, height=6, wrap="word", bg="#06090E", fg="#A0AEC0", insertbackground="#E2E8F0", relief="flat", highlightbackground="#222A3A", highlightthickness=1, font=("Consolas", 9))
        self.message.pack(fill="both", expand=True)
        self.message.insert("end", "[SYSTEM] Initialization sequence ready. Start device pipeline.\n")
        self.message.configure(state="disabled")

    def _render_control_ui(self, parent):
        # Module 1: Hardware Core Power
        ttk.Label(parent, text="SYSTEM INITIALIZATION", style="CardTitle.TLabel").pack(anchor="w")
        power_row = ttk.Frame(parent, style="Card.TFrame")
        power_row.pack(fill="x", pady=(10, 18))
        ttk.Button(power_row, text="START WEIGH CELL", style="Start.TButton", command=self.start_machine).pack(side="left")
        ttk.Button(power_row, text="STOP INTEL CIRCUIT", style="Stop.TButton", command=self.stop_machine).pack(side="left", padx=10)

        # Module 2: Mass Receptor Simulator Layer
        ttk.Label(parent, text="SIMULATED MASS RECEPTOR LOAD", style="CardTitle.TLabel").pack(anchor="w")
        slider_row = ttk.Frame(parent, style="Card.TFrame")
        slider_row.pack(fill="x", pady=(10, 18))
        
        self.load_var = tk.DoubleVar(value=self.target_load)
        self.load_slider = tk.Scale(
            slider_row, from_=0, to=8200, orient="horizontal", resolution=1,
            variable=self.load_var, bg="#161B26", fg="#A0AEC0", troughcolor="#0D111A",
            activebackground="#00E5FF", highlightthickness=0, command=self._on_slider_adjustment, length=480
        )
        self.load_slider.pack(fill="x")
        self.load_lbl_hint = ttk.Label(slider_row, text="Current Targeted Receptor Mass: 120.0000 g", style="SubTitle.TLabel")
        self.load_lbl_hint.pack(anchor="w", pady=(4, 0))

        # Module 3: Metrological Local Calibration Matrix Setup
        ttk.Label(parent, text="METROLOGIC ALGORITHMS & CALIBRATION", style="CardTitle.TLabel").pack(anchor="w")
        cal_grid = ttk.Frame(parent, style="Card.TFrame")
        cal_grid.pack(fill="x", pady=(10, 14))
        cal_grid.columnconfigure(0, weight=1)
        cal_grid.columnconfigure(1, weight=1)

        # Column Left: Manual Multiplier
        entry_container_1 = ttk.Frame(cal_grid, style="Card.TFrame")
        entry_container_1.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(entry_container_1, text="Manual Scaling Multiplier", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self.manual_scale_str = tk.StringVar(value="1.000000")
        self.entry_scale = ttk.Entry(entry_container_1, textvariable=self.manual_scale_str)
        self.entry_scale.pack(fill="x", pady=(0, 6))
        ttk.Button(entry_container_1, text="Apply Matrix Factor", style="Action.TButton", command=self.apply_manual_scaling).pack(fill="x")

        # Column Right: Auto Target
        entry_container_2 = ttk.Frame(cal_grid, style="Card.TFrame")
        entry_container_2.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(entry_container_2, text="Auto-Scaling Target Mass (g)", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self.auto_ref_str = tk.StringVar(value="500.0")
        self.entry_ref = ttk.Entry(entry_container_2, textvariable=self.auto_ref_str)
        self.entry_ref.pack(fill="x", pady=(0, 6))
        ttk.Button(entry_container_2, text="Compute Auto-Scale", style="Action.TButton", command=self.execute_auto_scale).pack(fill="x")

        # Module 4: Local Interface Manual Diagnostics
        footer_triggers = ttk.Frame(parent, style="Card.TFrame")
        footer_triggers.pack(fill="x", pady=(0, 18))
        ttk.Button(footer_triggers, text="Zero-Scaling Base", style="Action.TButton", command=self.execute_zero_scaling).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(footer_triggers, text="Tare Container Offset", style="Action.TButton", command=self.execute_tare).pack(side="left", expand=True, fill="x", padx=4)
        ttk.Button(footer_triggers, text="Reset Pipeline Calibration", style="Action.TButton", command=self.reset_entire_pipeline).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # Module 5: RS232 Command Hardware Emulation Console Intercept
        ttk.Label(parent, text="RS232 SERIAL TELEMETRY INTERFACE CONSOLE", style="CardTitle.TLabel").pack(anchor="w")
        command_box = ttk.Frame(parent, style="Card.TFrame")
        command_box.pack(fill="x", pady=(10, 0))
        
        entry_row = ttk.Frame(command_box, style="Card.TFrame")
        entry_row.pack(fill="x")
        self.command_var = tk.StringVar(value="ESC T")
        self.command_entry = ttk.Entry(entry_row, textvariable=self.command_var, font=("Consolas", 10))
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(entry_row, text="Transmit Frame", style="Action.TButton", command=self.send_command).pack(side="right")
        
        ttk.Label(command_box, text="Protocol Strings: ESC T, ESC W, ESC Z, ESC P, ESC S, ESC F1_, ESC F3_, ESC X1_, ESC X2_", style="SubTitle.TLabel").pack(anchor="w", pady=(6, 0))

    def _log(self, text):
        self.message.configure(state="normal")
        self.message.insert("end", text + "\n")
        self.message.see("end")
        self.message.configure(state="disabled")

    def _set_command_status(self, text):
        self.command_status_text.set(f"RS232: {text.upper()}")

    def _on_slider_adjustment(self, val):
        try:
            self.target_load = float(val)
        except ValueError:
            self.target_load = 0.0
        self.load_lbl_hint.configure(text=f"Current Targeted Receptor Mass: {self.target_load:,.4f} g")

    def _generate_live_signal(self):
        """Generates continuous physical transducer inputs matched with structural micro-fluctuations."""
        environmental_noise = random.uniform(-0.024, 0.024)
        vibration_drift = 0.0012 * self.noise_seed
        self.noise_seed = (self.noise_seed + 0.5) % 500.0
        return max(0.0, self.simulated_load + environmental_noise + vibration_drift)

    def _process_calibrated_weight(self, source_signal):
        """Converts raw voltage sensor telemetry streams into final legal metrology outputs."""
        return ((source_signal - self.zero_reference) * self.scale_factor) - self.tare_offset

    def start_machine(self):
        if self.machine_running:
            return
        self.machine_running = True
        self.status_text.set("ONLINE | METROLOGY RUNNING")
        self._log("[SYSTEM] Local processor loop initiated.")

    def stop_machine(self):
        if not self.machine_running:
            return
        self.machine_running = False
        self.blink_on = False
        self.status_text.set("SYSTEM OFFLINE")
        self.blinker_canvas.itemconfig(self.blinker_node, fill="#2D3748", outline="#1A202C")
        self.display_text.set("OFFLINE")
        self._log("[SYSTEM] Local processor loop suspended.")

    def apply_manual_scaling(self):
        try:
            factor = float(self.manual_scale_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid numerical configuration factor. Operation aborted.")
            return
        if factor <= 0:
            messagebox.showerror("Range Fault", "Metrological conversion scaling factor must scale above absolute zero.")
            return
        self.scale_factor = factor
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._log(f"[CAL] Local manual scale factor reassigned to: {self.scale_factor:.6f}")

    def execute_zero_scaling(self):
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.zero_reference = current_raw
        self.zero_text.set(f"Zero Ref   : {self.zero_reference:,.4f} g")
        self._log(f"[CAL] Zero-point base calibration latched at: {self.zero_reference:,.4f} g")

    def execute_tare(self):
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.tare_offset = self._process_calibrated_weight(current_raw)
        self.tare_text.set(f"Tare Base  : {self.tare_offset:,.4f} g")
        self._log(f"[CAL] Container envelope compensation matrix saved: {self.tare_offset:,.4f} g")

    def execute_auto_scale(self):
        try:
            reference_weight = float(self.auto_ref_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Target dynamic verification point parsing failure. Numerical input required.")
            return
        if reference_weight <= 0:
            messagebox.showerror("Range Fault", "Verification targets cannot track against a null or negative coordinate system.")
            return

        sample_raw = self._generate_live_signal() if self.machine_running else max(self.simulated_load, 0.001)
        delta_span = sample_raw - self.zero_reference
        if abs(delta_span) < 1e-5:
            messagebox.showerror("Algorithmic Fault", "Sensor differential range span is too close to zero base line reference. Auto-scale computation terminated.")
            return

        self.scale_factor = reference_weight / delta_span
        self.manual_scale_str.set(f"{self.scale_factor:.6f}")
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._log(f"[CAL] Automated adjustment linear scaling complete using standard target: {reference_weight:.4f} g")

    def reset_entire_pipeline(self):
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Multiplier : 1.000000")
        self.zero_text.set("Zero Ref   : 0.0000 g")
        self.tare_text.set("Tare Base  : 0.0000 g")
        self._log("[CAL] Dynamic calibration pipelines flushed. Local memory values reset to unity parameters.")

    # --- RS232 Engine Implementation Block ---
    def _normalize_command(self, txt):
        normalized = txt.strip()
        if not normalized:
            return ""
        normalized = normalized.replace("\\x1b", "ESC").replace("\x1b", "ESC").replace("\u001b", "ESC")
        return " ".join(normalized.split()).upper()

    def send_command(self):
        raw_cmd = self.command_var.get()
        if not raw_cmd.strip():
            self._set_command_status("EMPTY FRAME")
            return

        normalized = self._normalize_command(raw_cmd)
        response_frame = self.process_rs232_command(normalized)
        self.command_history.append((raw_cmd, response_frame))
        self._log(f"[RS232 RX] {raw_cmd.strip()} -> [TX] {response_frame}")
        self._set_command_status(response_frame)

    def process_rs232_command(self, cmd):
        handlers = {
            "ESC T": self._cmd_tare_or_zero,
            "ESC U": self._cmd_tare_key,
            "ESC V": self._cmd_zero_key,
            "ESC W": self._cmd_start_adjustment,
            "ESC Z": self._cmd_internal_calibration,
            "ESC P": self._cmd_print_trigger_data,
            "ESC S": self._cmd_restart_self_test,
            "ESC ?": self._cmd_apply_internal_adjustment_weight,
            "ESC @": self._cmd_lift_internal_adjustment_weight,
            "ESC S1_": self._cmd_start_adjustment,
            "ESC F1_": self._cmd_cal_function_key,
            "ESC F2_": self._cmd_enter_key,
            "ESC F3_": self._cmd_zero_key,
            "ESC F4_": self._cmd_tare_key,
            "ESC S3_": self._cmd_cancel_function,
            "ESC X0_": self._cmd_internal_calibration,
            "ESC X1_": self._cmd_print_model_type,
            "ESC X2_": self._cmd_print_serial_number,
        }

        if cmd in handlers:
            return handlers[cmd]()
        if cmd in {"ESC TARE", "TARE"}:
            return self._cmd_tare_or_zero()
        if cmd in {"ESC ZERO", "ZERO"}:
            return self._cmd_zero_key()

        return f"ERR: INVALID FRAME [{cmd}]"

    def _cmd_tare_or_zero(self):
        self.execute_tare()
        self.adjustment_state = "tared"
        return "TARE/ZERO ACK"

    def _cmd_tare_key(self):
        self.execute_tare()
        return "TARE ACK"

    def _cmd_zero_key(self):
        self.execute_zero_scaling()
        return "ZERO ACK"

    def _cmd_start_adjustment(self):
        self.adjustment_state = "external adjustment"
        self._set_command_status("CAL.EXT")
        self.execute_auto_scale()
        return "EXT CAL RUNNING"

    def _cmd_internal_calibration(self):
        self.adjustment_state = "internal calibration"
        self._set_command_status("CAL.INT")
        if not self.machine_running:
            self.start_machine()
        self.execute_tare()
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Multiplier : 1.000000")
        return "INT CAL RUNNING"

    def _cmd_restart_self_test(self):
        self.self_test_active = True
        self.adjustment_state = "self-test"
        self.reset_entire_pipeline()
        self.stop_machine()
        self.self_test_active = False
        return "DIAGNOSTIC COMPLETE"

    def _cmd_apply_internal_adjustment_weight(self):
        self.adjustment_state = "internal weight applied"
        return "INT MASS ENGAGED"

    def _cmd_lift_internal_adjustment_weight(self):
        self.adjustment_state = "internal weight lifted"
        return "INT MASS DISENGAGED"

    def _cmd_cal_function_key(self):
        return self._cmd_start_adjustment()

    def _cmd_enter_key(self):
        return "KEYPRESS ENTER ACK"

    def _cmd_cancel_function(self):
        self.adjustment_state = "idle"
        self._set_command_status("CANCELLED")
        return "OP CANCELLED"

    def _cmd_print_model_type(self):
        return "MODEL: SARTORIUS-WZB-VIRTUAL"

    def _cmd_print_serial_number(self):
        return "S/N: SIM-WZB-202606"

    def _cmd_print_weight(self):
        return f"WT + {self.last_display_value:,.4f} g"

    def _cmd_print_trigger_data(self):
        return self._cmd_print_weight()

    # --- Asynchronous Logic Loop Orchestration ---
    def _simulation_engine_tick(self):
        """Asynchronous cycle managing continuous measurement logic updates."""
        if self.machine_running:
            # Emulates physical damping inertia delay of mechanical system load transitions
            self.simulated_load += (self.target_load - self.simulated_load) * 0.12
            raw_signal = self._generate_live_signal()
            transformed_net_weight = self._process_calibrated_weight(raw_signal)
            self.last_display_value = transformed_net_weight
            
            # Formatted readout displaying metrological 4-decimal precision
            self.display_text.set(f"{transformed_net_weight:,.4f} g")
            self.raw_text.set(f"Raw Signal : {raw_signal:,.4f} g")
            
            if self.adjustment_state == "external adjustment":
                self.status_text.set("CAL.EXT" if not self.blink_on else "CALRUN")
            elif self.adjustment_state == "internal calibration":
                self.status_text.set("CAL.INT" if not self.blink_on else "CALRUN")
            elif self.self_test_active:
                self.status_text.set("DIAGNOSTIC RUNNING")
            else:
                self.status_text.set("ONLINE | METROLOGY RUNNING" if not self.blink_on else "ONLINE | DATA BUS ACTIVE")
        else:
            self.display_text.set("OFFLINE")
            self.raw_text.set(f"Raw Signal : {self.simulated_load:,.4f} g")

        self.after(50, self._simulation_engine_tick)

    def _status_blinker_tick(self):
        """Handles background cyclic logic for the hardware visual status beacon."""
        if self.machine_running:
            self.blink_on = not self.blink_on
            glow_on = "#00E676"   # Neon emerald green pulse state
            glow_off = "#004D2C"  # Dark forest tracking state
            
            fill_color = glow_on if self.blink_on else glow_off
            outline_color = "#B9F6CA" if self.blink_on else "#002314"
            self.blinker_canvas.itemconfig(self.blinker_node, fill=fill_color, outline=outline_color)
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