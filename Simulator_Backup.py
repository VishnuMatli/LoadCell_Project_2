import random
import tkinter as tk
from tkinter import ttk, messagebox


class ModernWeighCellSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sartorius WZB Series - Virtual Weigh Cell Environment")
        self.geometry("1080x780")
        self.minsize(1040, 720)
        
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
        
        # Command Bus Buffers & Transceiver Registers
        self.command_history = []
        self.xbpi_address = 0x00
        
        # String Variables for Dynamic UI Telemetry Tracking
        self.status_text = tk.StringVar(value="SYSTEM OFFLINE")
        self.display_text = tk.StringVar(value="------")
        self.raw_text = tk.StringVar(value="Raw Signal : 0.0000 g")
        self.scale_text = tk.StringVar(value="Multiplier : 1.000000")
        self.zero_text = tk.StringVar(value="Zero Ref   : 0.0000 g")
        self.tare_text = tk.StringVar(value="Tare Base  : 0.0000 g")
        self.command_status_text = tk.StringVar(value="BUS PROTOCOL CONSOLE: STANDBY")

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

        # Global Structural Framework
        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card, relief="flat", borderwidth=0)
        
        style.configure("MainTitle.TLabel", background=bg_main, foreground=text_primary, font=("Segoe UI", 16, "bold"))
        style.configure("SubTitle.TLabel", background=bg_main, foreground=text_muted, font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background=bg_card, foreground=accent_blue, font=("Segoe UI", 11, "bold"))
        style.configure("CardTitleX.TLabel", background=bg_card, foreground=accent_green, font=("Segoe UI", 11, "bold"))
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
        root_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Workspace Header Module
        header_frame = ttk.Frame(root_container, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(header_frame, text="SARTORIUS MULTI-PROTOCOL INTERFACE TESTING SUITE", style="MainTitle.TLabel").pack(anchor="w")
        ttk.Label(header_frame, text="Dual-Standard physical layer simulation client featuring synchronized RS232-SBI ASCII & xBPI Binary Transceiver Cores.", style="SubTitle.TLabel").pack(anchor="w", pady=(2, 0))

        # Main Interface Layout Splitting
        workspace = ttk.Frame(root_container, style="TFrame")
        workspace.pack(fill="both", expand=True)
        workspace.columnconfigure(0, weight=1)  
        workspace.columnconfigure(1, weight=1)  

        left_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self._render_control_ui(left_panel)
        self._render_telemetry_ui(right_panel)

    def _render_telemetry_ui(self, parent):
        ttk.Label(parent, text="METROLOGICAL REAL-TIME READOUT", style="CardTitle.TLabel").pack(anchor="w")

        # Core Transflective LCD Emulation Grid
        display_canvas = tk.Frame(parent, bg="#06090E", highlightbackground="#222A3A", highlightthickness=1)
        display_canvas.pack(fill="x", pady=(10, 10))

        unit_overlay = tk.Label(display_canvas, text="NET WT", bg="#06090E", fg="#4A5568", font=("Segoe UI", 9, "bold"))
        unit_overlay.pack(anchor="nw", padx=12, pady=(8, 0))

        self.display_label = tk.Label(
            display_canvas,
            textvariable=self.display_text,
            bg="#06090E",
            fg="#00E5FF",
            font=("Consolas", 38, "bold"),
            anchor="e",
            padx=16,
            pady=8
        )
        self.display_label.pack(fill="x")

        # Dynamic System Pulse Beacon Strip
        status_bar = ttk.Frame(parent, style="Card.TFrame")
        status_bar.pack(fill="x", pady=(0, 10))

        self.blinker_canvas = tk.Canvas(status_bar, width=24, height=24, bg="#161B26", highlightthickness=0)
        self.blinker_canvas.pack(side="left")
        self.blinker_node = self.blinker_canvas.create_oval(4, 4, 20, 20, fill="#2D3748", outline="#1A202C")

        ttk.Label(status_bar, textvariable=self.status_text, style="Metric.TLabel").pack(side="left", padx=8)

        # Real-Time Core Bus Telemetry Matrix
        ttk.Label(parent, text="INSTRUMENTATION PIPELINE CRITICAL REGISTERS", style="CardTitle.TLabel").pack(anchor="w", pady=(6, 4))
        matrix_box = tk.Frame(parent, bg="#0D111A", highlightbackground="#1F2937", highlightthickness=1, padx=12, pady=10)
        matrix_box.pack(fill="x", pady=(0, 14))

        ttk.Label(matrix_box, textvariable=self.raw_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.scale_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.zero_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.tare_text, style="Metric.TLabel", background="#0D111A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.command_status_text, style="Metric.TLabel", background="#0D111A", foreground="#00E676").pack(anchor="w", pady=2)

        # Integrated RS232/xBPI Serial Transceiver Logs Window
        ttk.Label(parent, text="UNIVERSAL SERIAL BUS TRANSPOND MONITOR (HEX & ASCII LOGS)", style="CardTitle.TLabel").pack(anchor="w", pady=(6, 4))
        self.message = tk.Text(parent, height=8, wrap="word", bg="#06090E", fg="#A0AEC0", insertbackground="#E2E8F0", relief="flat", highlightbackground="#222A3A", highlightthickness=1, font=("Consolas", 9))
        self.message.pack(fill="both", expand=True)
        self.message.insert("end", "[CORE] Multi-Standard hardware serial physical driver maps successfully.\n")
        self.message.configure(state="disabled")

    def _render_control_ui(self, parent):
        # Module 1: Hardware Core Power
        ttk.Label(parent, text="SYSTEM INITIALIZATION", style="CardTitle.TLabel").pack(anchor="w")
        power_row = ttk.Frame(parent, style="Card.TFrame")
        power_row.pack(fill="x", pady=(8, 14))
        ttk.Button(power_row, text="START WEIGH CELL", style="Start.TButton", command=self.start_machine).pack(side="left")
        ttk.Button(power_row, text="STOP INTEL CIRCUIT", style="Stop.TButton", command=self.stop_machine).pack(side="left", padx=10)

        # Module 2: Mass Receptor Simulator Layer
        ttk.Label(parent, text="SIMULATED MASS RECEPTOR LOAD CONTROL", style="CardTitle.TLabel").pack(anchor="w")
        slider_row = ttk.Frame(parent, style="Card.TFrame")
        slider_row.pack(fill="x", pady=(8, 14))
        
        self.load_var = tk.DoubleVar(value=self.target_load)
        self.load_slider = tk.Scale(
            slider_row, from_=0, to=8200, orient="horizontal", resolution=1,
            variable=self.load_var, bg="#161B26", fg="#A0AEC0", troughcolor="#0D111A",
            activebackground="#00E5FF", highlightthickness=0, command=self._on_slider_adjustment, length=440
        )
        self.load_slider.pack(fill="x")
        
        # Dedicated Injection Preset Buttons
        preset_row = ttk.Frame(slider_row, style="Card.TFrame")
        preset_row.pack(fill="x", pady=(4, 0))
        ttk.Button(preset_row, text="Inject 535.0000 g Reference Load", style="Action.TButton", command=lambda: self._inject_preset_load(535.0)).pack(side="left")
        ttk.Button(preset_row, text="Clear Load (0.0000 g)", style="Action.TButton", command=lambda: self._inject_preset_load(0.0)).pack(side="left", padx=10)
        
        self.load_lbl_hint = ttk.Label(slider_row, text="Current Targeted Receptor Mass: 120.0000 g", style="SubTitle.TLabel")
        self.load_lbl_hint.pack(anchor="w", pady=(4, 0))

        # Module 3: Local Local Manual Calibration Trimming
        ttk.Label(parent, text="MANUAL HARDWARE TRIMMING STATIONS", style="CardTitle.TLabel").pack(anchor="w")
        cal_grid = ttk.Frame(parent, style="Card.TFrame")
        cal_grid.pack(fill="x", pady=(8, 10))
        cal_grid.columnconfigure(0, weight=1)
        cal_grid.columnconfigure(1, weight=1)

        # Column Left: Manual Multiplier
        entry_container_1 = ttk.Frame(cal_grid, style="Card.TFrame")
        entry_container_1.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Label(entry_container_1, text="Manual Scaling Factor", style="FieldLabel.TLabel").pack(anchor="w", pady=(0, 2))
        self.manual_scale_str = tk.StringVar(value="1.000000")
        self.entry_scale = ttk.Entry(entry_container_1, textvariable=self.manual_scale_str)
        self.entry_scale.pack(fill="x", pady=(0, 4))
        ttk.Button(entry_container_1, text="Apply Scalar Multiplier", style="Action.TButton", command=self.apply_manual_scaling).pack(fill="x")

        # Column Right: Auto Target
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

        # Module 4: Dual Standard Serial Transceiver Intercept Terminal
        ttk.Label(parent, text="SERIAL REMOTE COMMAND CONSOLE LINK", style="CardTitleX.TLabel").pack(anchor="w")
        command_box = ttk.Frame(parent, style="Card.TFrame")
        command_box.pack(fill="x", pady=(8, 0))
        
        # Mode Controller Switch Tabs
        self.protocol_mode = "xBPI"  
        mode_row = ttk.Frame(command_box, style="Card.TFrame")
        mode_row.pack(fill="x", pady=(0, 4))
        self.lbl_mode_indicator = ttk.Label(mode_row, text="Active Protocol Decoder: SARTORIUS xBPI COMPILER MODE (BINARY TRANSLATION)", font=("Segoe UI", 9, "bold"), foreground="#000000")
        self.lbl_mode_indicator.pack(side="left")
        
        entry_row = ttk.Frame(command_box, style="Card.TFrame")
        entry_row.pack(fill="x")
        self.command_var = tk.StringVar(value="04 01 09 1E 2C")  
        self.command_entry = ttk.Entry(entry_row, textvariable=self.command_var, font=("Consolas", 10))
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(entry_row, text="Transmit Frame", style="Action.TButton", command=self.send_command).pack(side="right")
        
        self.lbl_syntax_hint = ttk.Label(
            command_box, 
            text="xBPI Binary Frames (Hex): [04 01 09 1E 2C] Read Net | [04 01 09 16 24] Tare | [04 01 09 18 26] Zero\nSwitch to legacy mode via text interface: 'ESC T' / 'ESC W' / 'ESC Z'", 
            style="SubTitle.TLabel", justify="left"
        )
        self.lbl_syntax_hint.pack(anchor="w", pady=(4, 0))

    def _log(self, text):
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
        """Forces the sensor input layer to an explicit precise metric coordinate."""
        self.load_var.set(target_mass)
        self._on_slider_adjustment(target_mass)
        self._log(f"[HARDWARE] Automated mass injection device dispatched reference weight: {target_mass:,.4f} g onto pan.")

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
        self._log("[SYSTEM] Main core sensor loop running. Transducer data pipes opened.")

    def stop_machine(self):
        if not self.machine_running:
            return
        self.machine_running = False
        self.blink_on = False
        self.status_text.set("SYSTEM OFFLINE")
        self.blinker_canvas.itemconfig(self.blinker_node, fill="#2D3748", outline="#1A202C")
        self.display_text.set("OFFLINE")
        self._log("[SYSTEM] Main core sensor loop stopped. Transducer data lines flushed.")

    def apply_manual_scaling(self):
        try:
            factor = float(self.manual_scale_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid numerical entry matrix. Input floating-point scaling parameters.")
            return
        if factor <= 0:
            messagebox.showerror("Range Fault", "Metrological conversion scaling vectors must execute above absolute zero configuration parameters.")
            return
        self.scale_factor = factor
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._log(f"[CAL] Local calibration array scaling updated to factor value: {self.scale_factor:.6f}")

    def execute_zero_scaling(self):
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.zero_reference = current_raw
        self.zero_text.set(f"Zero Ref   : {self.zero_reference:,.4f} g")
        self._log(f"[CAL] Local hardware static zero reference balance point stored at: {self.zero_reference:,.4f} g")

    def execute_tare(self):
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.tare_offset = self._process_calibrated_weight(current_raw)
        self.tare_text.set(f"Tare Base  : {self.tare_offset:,.4f} g")
        self._log(f"[CAL] Container mass compensation value latched into register: {self.tare_offset:,.4f} g")

    def execute_auto_scale(self):
        try:
            reference_weight = float(self.auto_ref_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Calibration target parsing failure. Float syntax required.")
            return
        if reference_weight <= 0:
            messagebox.showerror("Range Fault", "Internal linearization reference points must track above linear origin.")
            return

        sample_raw = self._generate_live_signal() if self.machine_running else max(self.simulated_load, 0.001)
        delta_span = sample_raw - self.zero_reference
        if abs(delta_span) < 1e-5:
            messagebox.showerror("Algorithmic Fault", "Sensor span too close to zero boundary conditions. Calibration matrix aborted.")
            return

        self.scale_factor = reference_weight / delta_span
        self.manual_scale_str.set(f"{self.scale_factor:.6f}")
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._log(f"[CAL] Dynamic span validation auto-scaling factor resolved against mass reference standard {reference_weight:.4f} g.")

    def reset_entire_pipeline(self):
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Multiplier : 1.000000")
        self.zero_text.set("Zero Ref   : 0.0000 g")
        self.tare_text.set("Tare Base  : 0.0000 g")
        self._log("[CAL] Metrological alignment data registers purged. Reverted to raw sensor unity profile.")

    # --- Core Serial Remote Link Engines ---
    def send_command(self):
        raw_input = self.command_var.get().strip()
        if not raw_input:
            self._set_command_status("EMPTY TELEMETRY FRAME")
            return

        # Decoder Routing Matrix
        if raw_input.upper().startswith("ESC") or len(raw_input.split()) == 0 or not all(c in "0123456789ABCDEFabcdef " for c in raw_input):
            self.protocol_mode = "RS232/SBI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: LEGACY RS232-SBI TERMINAL MODE (ASCII STRINGS)", foreground="#FF3D71")
            normalized_ascii = raw_input.upper()
            tx_frame = self._process_legacy_rs232_ascii(normalized_ascii)
            self.command_history.append((raw_input, tx_frame))
            self._log(f"[RS232 RX] ASCII String -> '{raw_input}' | [TX Response] -> {tx_frame}")
            self._set_command_status(tx_frame)
        else:
            self.protocol_mode = "xBPI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: SARTORIUS xBPI COMPILER MODE (BINARY TRANSLATION)", foreground="#000000")
            try:
                byte_array = bytes.fromhex(raw_input)
                tx_bytes = self._process_binary_xbpi_frame(byte_array)
                tx_hex_string = " ".join(f"{b:02X}" for b in tx_bytes)
                self.command_history.append((raw_input, tx_hex_string))
                self._log(f"[xBPI RX] Binary Frame  ->  {raw_input} | [TX Response] ->  {tx_hex_string}")
                self._set_command_status(f"TX SUCCESS | FRAME DETECTED: {tx_hex_string[:14]}...")
            except ValueError:
                self._log(f"[xBPI BUS FAULT] Compiled byte streams failed conversion matrices. Verification structure invalid.")
                self._set_command_status("FRAME STRUCT ERROR")

    def _process_binary_xbpi_frame(self, data: bytes) -> bytes:
        """Processes binary incoming telegrams based on structural Modulo-256 validation rules."""
        if len(data) < 3:
            return bytes([0x03, 0x41, 0x95])  

        length_byte = data[0]
        if len(data) != length_byte + 1: 
            return bytes([0x03, 0x41, 0x95])  

        # Modulo-256 Checksum Validation
        expected_checksum = data[-1]
        computed_checksum = sum(data[:-1]) % 256
        if computed_checksum != expected_checksum:
            return bytes([0x03, 0x41, 0x92])  

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
            model_bytes = "IS64FEG         ".encode('ascii')
            response_frame.extend(bytes([0x49])) 
            response_frame.extend(model_bytes)
            
        elif function_number == 0x28: 
            self.adjustment_state = "external adjustment"
            self.execute_auto_scale()
            response_frame.extend(bytes([0x00]))  
            
        elif function_number == 0x29: 
            self.adjustment_state = "idle"
            response_frame.extend(bytes([0x00]))  
            
        else:
            response_frame.extend(bytes([0x01, 0x01]))  

        final_tx_packet = bytearray()
        tx_length = len(response_frame) + 2
        final_tx_packet.append(tx_length)
        final_tx_packet.append(0x41)  
        final_tx_packet.extend(response_frame)
        
        packet_chk = sum(final_tx_packet) % 256
        final_tx_packet.append(packet_chk)
        
        return bytes(final_tx_packet)

    def _process_legacy_rs232_ascii(self, cmd: str) -> str:
        """Processes core ASCII instructions."""
        if cmd in {"ESC T", "ESC TARE", "TARE"}:
            self.execute_tare()
            self.adjustment_state = "tared"
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
            if not self.machine_running:
                self.start_machine()
            self.execute_tare()
            self.scale_factor = 1.0
            self.manual_scale_str.set("1.000000")
            self.scale_text.set("Multiplier : 1.000000")
            return "INT CAL RUNNING"
        elif cmd == "ESC S":
            self.self_test_active = True
            self.adjustment_state = "self-test"
            self.reset_entire_pipeline()
            self.stop_machine()
            self.self_test_active = False
            return "DIAGNOSTIC COMPLETE"
        elif cmd == "ESC P":
            return f"WT + {self.last_display_value:,.4f} g"
        elif cmd == "ESC X1_":
            return "MODEL: SARTORIUS-WZB-VIRTUAL"
        elif cmd == "ESC X2_":
            return "S/N: SIM-WZB-202606"
        elif cmd == "ESC S3_":
            self.adjustment_state = "idle"
            return "OP CANCELLED"
        else:
            return f"ERR: COMMAND UNRECOGNIZED [{cmd}]"

    # --- Asynchronous Logic Loop Orchestration ---
    def _simulation_engine_tick(self):
        """Asynchronous cycle managing continuous measurement logic updates."""
        if self.machine_running:
            self.simulated_load += (self.target_load - self.simulated_load) * 0.12
            raw_signal = self._generate_live_signal()
            transformed_net_weight = self._process_calibrated_weight(raw_signal)
            self.last_display_value = transformed_net_weight
            
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
            glow_on = "#00E676"   
            glow_off = "#004D2C"  
            
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