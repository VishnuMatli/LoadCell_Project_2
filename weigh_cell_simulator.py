import random
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class ModernWeighCellSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sartorius CAS Suite - Weigh Cell Emulation Environment")
        self.geometry("1420x860")
        self.minsize(1200, 780)
        
        # 1. Core Metrological Registry States
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
        
        # --- CAS PARAMETER LOGIC STATE REGISTERS ---
        # 1.1 Balance Parameters
        self.active_env_filter = "1.1.1.2"        
        self.active_app_filter = "1.1.2.1"        
        self.active_stability_range = "1.1.3.4"   
        self.active_stability_delay = "1.1.4.2"   
        self.active_taring_mode = "1.1.5.2"       
        self.active_autozero = "1.1.6.1"          
        self.active_weight_unit = "1.1.7.2"       
        self.active_accuracy_digits = "1.1.8.1"   
        self.active_cal_func = "1.1.9.1"          
        self.active_adjust_process = "1.1.10.1"   
        self.active_zero_range = "1.1.11.2"       
        self.active_poweron_zero = "1.1.12.4"     
        self.active_poweron_tarezero = "1.1.13.1" 
        self.active_output_rate = "1.1.14.1"      
        self.active_isocal = "1.1.15.1"           
        
        # 1.9 General Settings Parameters
        self.active_menu_reset = "1.9.1.2"        

        # 2. Active Print Menu Parameters
        self.print_data_output = "3.1.1.1"        
        self.print_cancel_auto = "3.1.2.1"        
        self.print_cycle_auto = "3.1.3.1"         
        self.print_output_format = "3.1.4.1"      
        self.print_trigger_type = "3.2.1.2"       
        self.print_layout_format = "3.2.2.2"      
        self.print_appl_param = "3.2.3.2"         
        self.print_glp_protocol = "3.2.4.1"       
        
        # 2.3 PC Direct Parameters
        self.pc_decimal_separator = "3.3.1.1"     
        self.pc_output_format = "3.3.2.1"         

        # Digital Signal Processing Buffers
        self.filter_history_buffer = []
        self.is_currently_stable = True
        self.previous_weights_history = [0.0] * 5
        self.simulation_tick_rate_ms = 50         
        
        # Physical Transducer Stream File Buffers
        self.file_stream_buffer = []
        self.file_stream_index = 0
        self.is_file_stream_active = False
        self.loaded_file_path = ""
        self.adc_reference_scale = 535.0 / 44347000.0  
        self.command_history = []

        # 2. Variable Allocation
        self.load_var = tk.DoubleVar(value=self.target_load)
        self.status_text = tk.StringVar(value="EMULATOR BUS CORE: STANDBY")
        self.display_text = tk.StringVar(value="------")
        self.raw_text = tk.StringVar(value="Transducer Input: 0.0000 g")
        self.scale_text = tk.StringVar(value="Calibration Scale: 1.000000")
        self.zero_text = tk.StringVar(value="Zero Offset: 0.0000 g")
        self.tare_text = tk.StringVar(value="Tare Offset: 0.0000 g")
        self.command_status_text = tk.StringVar(value="REMOTE BUS CONTROL: STANDBY")
        self.stream_status_text = tk.StringVar(value="INPUT TRACK: BALANCED SLIDER")

        # 3. Apply Theme Styles & Build Responsive Layout Architecture
        self._apply_theme_styles()
        self._build_hardware_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_safe_close)

        # High-Fidelity Asynchronous Execution Loops
        self._scheduled_engine_loop_id = self.after(self.simulation_tick_rate_ms, self._simulation_engine_tick)
        self.after(350, self._status_blinker_tick)

    def _apply_theme_styles(self):
        """Initializes a slate dark theme based on the uploaded color scheme palette."""
        style = ttk.Style(self)
        style.theme_use("clam")
        
        bg_main = "#0F172A"       
        bg_card = "#1E293B"       
        border_color = "#334155"  
        text_primary = "#F8FAFC"  
        text_muted = "#94A3B8"    
        accent_blue = "#38BDF8"   
        accent_green = "#4ADE80"  

        self.configure(bg=bg_main)

        style.configure("TFrame", background=bg_main)
        style.configure("Card.TFrame", background=bg_card, relief="solid", borderwidth=1, lightcolor=border_color, darkcolor=border_color)
        style.configure("ScrollCard.TFrame", background=bg_card) 
        
        style.configure("MainTitle.TLabel", background=bg_main, foreground=text_primary, font=("Segoe UI", 16, "bold"))
        style.configure("SubTitle.TLabel", background=bg_main, foreground=text_muted, font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background=bg_card, foreground=accent_blue, font=("Segoe UI", 11, "bold"))
        style.configure("CardTitleX.TLabel", background=bg_card, foreground=accent_green, font=("Segoe UI", 11, "bold"))
        style.configure("Metric.TLabel", background=bg_card, foreground=text_primary, font=("Consolas", 10, "bold"))
        style.configure("FieldLabel.TLabel", background=bg_card, foreground=text_primary, font=("Segoe UI", 9, "bold"))

        style.configure("Start.TButton", font=("Segoe UI", 9, "bold"), padding=8, background="#22C55E", foreground="white", borderwidth=0)
        style.map("Start.TButton", background=[("active", "#16A34A")])

        style.configure("Stop.TButton", font=("Segoe UI", 9, "bold"), padding=8, background="#EF4444", foreground="white", borderwidth=0)
        style.map("Stop.TButton", background=[("active", "#DC2626")])

        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), padding=6, background="#334155", foreground=text_primary, borderwidth=1, bordercolor=border_color)
        style.map("Action.TButton", background=[("active", "#475569")])

        style.configure("Exit.TButton", font=("Segoe UI", 9, "bold"), padding=8, background="#EF4444", foreground="white", borderwidth=0)
        style.map("Exit.TButton", background=[("active", "#DC2626")])

        style.configure("TEntry", fieldbackground="#0F172A", foreground=text_primary, bordercolor=border_color, padding=6, font=("Consolas", 10))

        style.configure("Treeview", background="#1E293B", fieldbackground="#1E293B", foreground=text_primary, borderwidth=0, font=("Segoe UI", 9), rowheight=24)
        style.configure("Treeview.Heading", background="#334155", foreground=text_primary, font=("Segoe UI", 9, "bold"), padding=5)
        style.map("Treeview", background=[("selected", "#334155")], foreground=[("selected", "#38BDF8")])

    # =========================================================================
    # CORE REGS & METHOD ACTION LOGIC - DECLARED AT TOP TO ENSURE INTEGRITY
    # =========================================================================
    def _write_terminal_log(self, text):
        self.message.configure(state="normal")
        self.message.insert("end", text + "\n")
        self.message.see("end")
        self.message.configure(state="disabled")

    def _set_command_status(self, text):
        self.command_status_text.set(f"BUS REMOTE TELEMETRY STATUS: {text.upper()}")

    def _on_cas_menu_node_click(self, event):
        selected_node = self.cas_tree.selection()
        if not selected_node:
            return
            
        node_data = self.cas_tree.item(selected_node[0])
        node_values = node_data.get("values", "")
        
        if node_values:
            param_group, target_code = node_values[0], node_values[1]
            
            # --- ROUTING FOR LEVEL 1.1 SETUPS (BALANCE) ---
            if param_group == "1.1.1":
                self.active_env_filter = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Ambient noise factor updated -> {target_code}")
            elif param_group == "1.1.2":
                self.active_app_filter = target_code
                self.filter_history_buffer.clear()
                self._write_terminal_log(f"[CAS SETTINGS] Digital DSP filter window modified -> {target_code}")
            elif param_group == "1.1.3":
                self.active_stability_range = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Metrological confirmation delta set -> {target_code}")
            elif param_group == "1.1.4":
                self.active_stability_delay = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Latch stability timing window set -> {target_code}")
            elif param_group == "1.1.5":
                self.active_taring_mode = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Taring state parameter assigned -> {target_code}")
            elif param_group == "1.1.6":
                self.active_autozero = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Origin drift tracking auto-adjust -> {target_code}")
            elif param_group == "1.1.7":
                self.active_weight_unit = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Instrumentation measurement base unit assigned -> {target_code}")
            elif param_group == "1.1.8":
                self.active_accuracy_digits = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Readout display numerical truncation pattern -> {target_code}")
            elif param_group == "1.1.9":
                self.active_cal_func = target_code
                self._write_terminal_log(f"[CAS SETTINGS] External calibration path profile mapped -> {target_code}")
                if target_code == "1.1.9.10":
                    self._write_terminal_log("[SECURITY LOCK] Balance physical interface button keys are BLOCKED.")
            elif param_group == "1.1.10":
                self.active_adjust_process = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Pre-calibration pipeline execution structure -> {target_code}")
            elif param_group == "1.1.11":
                self.active_zero_range = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Manual zero-point threshold range limit -> {target_code}")
            elif param_group == "1.1.12":
                self.active_poweron_zero = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Power-on offset tolerance range bounds -> {target_code}")
            elif param_group == "1.1.13":
                self.active_poweron_tarezero = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Power-on tracking data register clear parameter -> {target_code}")
            elif param_group == "1.1.14":
                self.active_output_rate = target_code
                self._reconfigure_asynchronous_clock_intervals(target_code)
            elif param_group == "1.1.15":
                self.active_isocal = target_code
                self._write_terminal_log(f"[CAS SETTINGS] Automatic internal IsoCal compliance flags modified -> {target_code}")
            
            # --- ROUTING FOR LEVEL 2.x SETUPS (ACTIVE PRINT MENU) ---
            elif param_group == "3.1.1":
                self.print_data_output = target_code
                self._write_terminal_log(f"[CAS PRINT] Serial data output trigger reconfigured -> {target_code}")
            elif param_group == "3.1.2":
                self.print_cancel_auto = target_code
                self._write_terminal_log(f"[CAS PRINT] Automatic output command cancellation flag -> {target_code}")
            elif param_group == "3.1.3":
                self.print_cycle_auto = target_code
                self._write_terminal_log(f"[CAS PRINT] Cycle rate descriptor for auto printing -> {target_code}")
            elif param_group == "3.1.4":
                self.print_output_format = target_code
                self._write_terminal_log(f"[CAS PRINT] Frame packet character size string set -> {target_code}")
            elif param_group == "3.2.1":
                self.print_trigger_type = target_code
                self._write_terminal_log(f"[CAS PRINT] Print key press synchronization mode -> {target_code}")
            elif param_group == "3.2.2":
                self.print_layout_format = target_code
                self._write_terminal_log(f"[CAS PRINT] Output layout and identification rules mapped -> {target_code}")
            elif param_group == "3.2.3":
                self.print_appl_param = target_code
                self._write_terminal_log(f"[CAS PRINT] Print Application parameters status -> {target_code}")
            elif param_group == "3.2.4":
                self.print_glp_protocol = target_code
                self._write_terminal_log(f"[CAS PRINT] GLP QA compliance report state -> {target_code}")

            # --- ROUTING FOR LEVEL 3.x SETUPS (PC DIRECT PARAMETERS) ---
            elif param_group == "3.3.1":
                self.pc_decimal_separator = target_code
                self._write_terminal_log(f"[CAS PC-DIRECT] Radix separator format mutated -> {target_code}")
            elif param_group == "3.3.2":
                self.pc_output_format = target_code
                self._write_terminal_log(f"[CAS PC-DIRECT] Bus content encoding restriction array -> {target_code}")

            # --- ROUTING FOR LEVEL 1.9 SETUPS (GENERAL SETTINGS) ---
            elif param_group == "1.9.1":
                if target_code == "1.9.1.1":
                    self._execute_factory_menu_reset()
                else:
                    self.active_menu_reset = "1.9.1.2"
                    
            self._set_command_status(f"REGISTRY CODE LINKED: {target_code}")

    def _on_slider_adjustment(self, val):
        try:
            self.target_load = float(val)
        except ValueError:
            self.target_load = 0.0
        self.load_lbl_hint.configure(text=f"Targeted Mass: {self.target_load:,.4f} g")

    def _inject_preset_load(self, target_mass):
        self.is_file_stream_active = False
        self.stream_status_text.set("INPUT TRACK: BALANCED SLIDER")
        self.load_var.set(target_mass)
        self._on_slider_adjustment(target_mass)
        self._write_terminal_log(f"[HARDWARE] Direct mass injection update complete: reference load standard {target_mass:,.4f} g pinned.")

    def _reconfigure_asynchronous_clock_intervals(self, code):
        rate_mappings = {
            "1.1.14.1": 50, "1.1.14.2": 40, "1.1.14.3": 100, "1.1.14.4": 50, "1.1.14.5": 40, "1.1.14.6": 20, "1.1.14.7": 10
        }
        self.simulation_tick_rate_ms = rate_mappings.get(code, 50)
        self._write_terminal_log(f"[CLOCK ROUTING] Main hardware update ticker modified to: {self.simulation_tick_rate_ms}ms")

    def _execute_factory_menu_reset(self):
        self.active_env_filter = "1.1.1.2"
        self.active_app_filter = "1.1.2.1"
        self.active_stability_range = "1.1.3.4"
        self.active_stability_delay = "1.1.4.2"
        self.active_taring_mode = "1.1.5.2"
        self.active_autozero = "1.1.6.1"
        self.active_weight_unit = "1.1.7.2"
        self.active_accuracy_digits = "1.1.8.1"
        self.active_cal_func = "1.1.9.1"
        self.active_adjust_process = "1.1.10.1"
        self.active_zero_range = "1.1.11.2"
        self.active_poweron_zero = "1.1.12.4"
        self.active_poweron_tarezero = "1.1.13.1"
        self.active_output_rate = "1.1.14.1"
        self.active_isocal = "1.1.15.1"
        
        self.print_data_output = "3.1.1.1"
        self.print_cancel_auto = "3.1.2.1"
        self.print_cycle_auto = "3.1.3.1"
        self.print_output_format = "3.1.4.1"
        self.print_trigger_type = "3.2.1.2"
        self.print_layout_format = "3.2.2.2"
        self.print_appl_param = "3.2.3.2"
        self.print_glp_protocol = "3.2.4.1"
        self.pc_decimal_separator = "3.3.1.1"
        self.pc_output_format = "3.3.2.1"
        
        self.active_menu_reset = "1.9.1.2"
        self.simulation_tick_rate_ms = 50
        self.filter_history_buffer.clear()
        self.reset_entire_pipeline()
        self._write_terminal_log("[REBOOT PIPELINE] Factory baseline profile configurations applied successfully.")
        messagebox.showinfo("Factory Reset", "CAS Database tables reset to standard defaults.")

    def reset_entire_pipeline(self):
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Calibration Scale: 1.000000")
        self.zero_text.set("Zero Offset: 0.0000 g")
        self.tare_text.set("Tare Offset: 0.0000 g")

    def apply_manual_scaling(self):
        if self.active_cal_func == "1.1.9.10":
            messagebox.showerror("Access Blocked", "Remote metrological calibration is currently BLOCKED (1.1.9.10).")
            return
        try:
            factor = float(self.manual_scale_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid numerical scalar format details.")
            return
        if factor <= 0: return
        self.scale_factor = factor
        self.scale_text.set(f"Calibration Scale: {self.scale_factor:.6f}")

    def execute_zero_scaling(self):
        if self.active_cal_func == "1.1.9.10": return
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        max_allowed_zero = 820.0 if self.active_zero_range == "1.1.11.4" else 164.0  
        if abs(current_raw) > max_allowed_zero:
            messagebox.showerror("Zero Error", f"Transducer offset out of tracking range parameters boundaries ({self.active_zero_range}).")
            return
        self.zero_reference = current_raw
        self.zero_text.set(f"Zero Offset: {self.zero_reference:,.4f} g")

    def execute_tare(self):
        if self.active_cal_func == "1.1.9.10": return
        if self.active_taring_mode == "1.1.5.2" and not self.is_currently_stable:
            self._write_terminal_log("[TARE BLOCKED] Waiting for data line output stability stabilization coordinates.")
            messagebox.showwarning("Metrological Lock", "Cannot execute tare while data streams are unstable.")
            return
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.tare_offset = self._process_calibrated_weight(current_raw)
        self.tare_text.set(f"Tare Offset: {self.tare_offset:,.4f} g")

    def execute_auto_scale(self):
        if self.active_cal_func == "1.1.9.10": return
        try:
            reference_weight = float(self.auto_ref_str.get().strip())
        except ValueError: return
        if reference_weight <= 0: return
        sample_raw = self._generate_live_signal() if self.machine_running else max(self.simulated_load, 0.001)
        delta_span = sample_raw - self.zero_reference
        if abs(delta_span) < 1e-5: return
        self.scale_factor = reference_weight / delta_span
        self.manual_scale_str.set(f"{self.scale_factor:.6f}")
        self.scale_text.set(f"Calibration Scale: {self.scale_factor:.6f}")

    def _import_sensor_log_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path: return
        try:
            temp_buffer = []
            with open(file_path, "r") as f:
                for line in f:
                    cleaned = line.strip()
                    if cleaned.startswith("ADC:"):
                        try: temp_buffer.append(float(cleaned.split(":")[1]))
                        except: continue
            if not temp_buffer: return
            self.file_stream_buffer = temp_buffer
            self.file_stream_index = 0
            self.loaded_file_path = os.path.basename(file_path)
            self.is_file_stream_active = True
            self.stream_status_text.set(f"INPUT TRACK: {self.loaded_file_path}")
            self._write_terminal_log(f"[INGESTION] Buffered {len(self.file_stream_buffer)} hardware lines from text frame.")
        except Exception as e: messagebox.showerror("I/O Error", str(e))

    def _toggle_stream_source_mode(self):
        if not self.file_stream_buffer: return
        self.is_file_stream_active = not self.is_file_stream_active
        self.stream_status_text.set(f"INPUT TRACK: {self.loaded_file_path}" if self.is_file_stream_active else "INPUT TRACK: BALANCED SLIDER")

    def start_machine(self):
        if self.machine_running: return
        if self.active_poweron_tarezero == "1.1.13.1":
            self.zero_reference = 0.0
            self.tare_offset = 0.0
        self.machine_running = True
        self.status_text.set("EMULATOR BUS CORE: ONLINE")
        self._write_terminal_log("[SYSTEM] Data telemetry stream processor active.")

    def stop_machine(self):
        if not self.machine_running: return
        self.machine_running = False
        self.blink_on = False
        self.status_text.set("EMULATOR BUS CORE: OFFLINE")
        self.blinker_canvas.itemconfig(self.blinker_node, fill="#64748B", outline="#334155")
        self.display_text.set("------")
        self._write_terminal_log("[SYSTEM] Data telemetry stream processor halted.")

    def send_command(self):
        raw_input = self.command_var.get().strip()
        if not raw_input: return
        if raw_input.upper().startswith("ESC") or len(raw_input.split()) == 0 or not all(c in "0123456789ABCDEFabcdef " for c in raw_input):
            self.protocol_mode = "RS232/SBI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: LEGACY RS232-SBI TERMINAL CORE", foreground="#EF4444")
            tx_frame = self._process_legacy_rs232_ascii(raw_input.upper())
            self._write_terminal_log(f"[RS232 RX] ASCII -> '{raw_input}' | [TX] -> {tx_frame}")
        else:
            self.protocol_mode = "xBPI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: SARTORIUS xBPI COMPILER LINK", foreground="#4ADE80")
            try:
                byte_array = bytes.fromhex(raw_input)
                tx_bytes = self._process_binary_xbpi_frame(byte_array)
                tx_hex_string = " ".join(f"{b:02X}" for b in tx_bytes)
                self._write_terminal_log(f"[xBPI RX] Binary Frame -> {raw_input} | [TX] -> {tx_hex_string}")
            except: pass

    def _process_binary_xbpi_frame(self, data: bytes) -> bytes:
        if len(data) < 3 or len(data) != data[0] + 1 or sum(data[:-1]) % 256 != data[-1]: return bytes([0x03, 0x41, 0x92])  
        function_number = data[3] if len(data) > 3 else 0x00
        response_frame = bytearray()
        if function_number == 0x1E:   
            response_frame.extend(bytes([0x48, 0x42, 0x14, 0x8F, 0x5C, 0x28, 0x34, 0x43]))
            self.adjustment_state = "idle"
        elif function_number == 0x16: self.execute_tare(); response_frame.extend(bytes([0x00]))  
        elif function_number == 0x18: self.execute_zero_scaling(); response_frame.extend(bytes([0x00]))  
        else: response_frame.extend(bytes([0x00]))
        final_tx_packet = bytearray([len(response_frame) + 2, 0x41]) + response_frame
        final_tx_packet.append(sum(final_tx_packet) % 256)
        return bytes(final_tx_packet)

    def _process_legacy_rs232_ascii(self, cmd: str) -> str:
        if cmd in {"ESC T", "TARE"}: self.execute_tare(); return "TARE ACK"
        if cmd in {"ESC V", "ZERO"}: self.execute_zero_scaling(); return "ZERO ACK"
        return f"WT + {self.last_display_value:,.4f} g"

    # =========================================================================
    # RESPONSIVE GRID WINDOW LAYOUT STRUCTURAL DEFINITION CORES
    # =========================================================================
    def _build_hardware_layout(self):
        """Constructs an integrated master container configuration supporting fully responsive scaling boundaries."""
        # Enable multi-axis window expansion calculations on root app context
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        master_content_container = ttk.Frame(self, style="TFrame")
        master_content_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Main configuration header bar row allocations
        header_frame = ttk.Frame(master_content_container, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=0)

        title_text_subcontainer = ttk.Frame(header_frame, style="TFrame")
        title_text_subcontainer.grid(row=0, column=0, sticky="nw")
        
        ttk.Label(title_text_subcontainer, text="SARTORIUS CAS CONFIGURATION & WEIGH SIMULATION SUITE", style="MainTitle.TLabel").pack(anchor="w")
        ttk.Label(title_text_subcontainer, text="High-precision multi-protocol test bench workspace running parallel xBPI and RS232 telemetry data registers.", style="SubTitle.TLabel").pack(anchor="w", pady=(2, 0))

        # Top-Right Anchor Alignment Matrix: Exit Button
        btn_exit = ttk.Button(header_frame, text="EXIT SYSTEM", style="Exit.TButton", command=self._on_safe_close)
        btn_exit.grid(row=0, column=1, sticky="ne", padx=(10, 0), pady=2)

        # Dynamic Grid Parent Workspace Frame Configuration (Crucial for Fluid Real-time Resizing)
        workspace = ttk.Frame(master_content_container, style="TFrame")
        workspace.pack(fill="both", expand=True)
        
        # Distribute proportional columns weights evenly (3 columns, equal expansion distribution metrics)
        workspace.columnconfigure(0, weight=1)  
        workspace.columnconfigure(1, weight=1)  
        workspace.columnconfigure(2, weight=1)  
        workspace.rowconfigure(0, weight=1)     # Expand dynamically vertical height rows bounds

        # Allocate children grid targets with global adaptive directional stickiness coordinates
        sidebar_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        sidebar_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        self._render_cas_sidebar_ui(sidebar_panel)

        left_panel = ttk.Frame(workspace, style="Card.TFrame", padding=0)
        left_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._render_scrolling_control_ui(left_panel)

        right_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0), pady=5)
        self._render_telemetry_ui(right_panel)

    def _render_cas_sidebar_ui(self, parent):
        ttk.Label(parent, text="DEVICE HARDWARE PARAMETER REGISTRY", style="CardTitleX.TLabel").pack(anchor="w", pady=(0, 10))
        
        tree_container = tk.Frame(parent, bg="#1E293B", highlightbackground="#334155", highlightthickness=1)
        tree_container.pack(fill="both", expand=True)
        
        v_scroll = tk.Scrollbar(tree_container, orient="vertical")
        h_scroll = tk.Scrollbar(tree_container, orient="horizontal")
        
        self.cas_tree = ttk.Treeview(
            tree_container, 
            yscrollcommand=v_scroll.set, 
            xscrollcommand=h_scroll.set, 
            selectmode="browse", 
            show="tree headings"
        )
        
        v_scroll.config(command=self.cas_tree.yview)
        h_scroll.config(command=self.cas_tree.xview)
        
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        self.cas_tree.pack(side="left", fill="both", expand=True)
        
        self.cas_tree.heading("#0", text="CAS Nested Parameter Tree Structure", anchor="w")
        self.cas_tree.column("#0", minwidth=450, width=580, stretch=True)

        # --- LEVEL 1 CORE PARAMETERS MENUS ---
        l1_setup = self.cas_tree.insert("", "end", text="1. Active Setup Menu", open=True)
        l1_print = self.cas_tree.insert("", "end", text="2. Active Print Menu", open=True)
        l1_device = self.cas_tree.insert("", "end", text="3. Active Device Menu")
        l1_app = self.cas_tree.insert("", "end", text="4. Active Application Menu")

        self.cas_tree.insert(l1_device, "end", text="Peripheral Bus Hardware Mapping [BLOCKED]")
        self.cas_tree.insert(l1_app, "end", text="User Calculation Registers [BLOCKED]")

        # --- LEVEL 2 SECTIONS MENUS ---
        l2_balance = self.cas_tree.insert(l1_setup, "end", text="1.1 Balance Settings", open=True)
        l2_general = self.cas_tree.insert(l1_setup, "end", text="1.9 General Settings", open=True)
        
        l2_print_comm = self.cas_tree.insert(l1_print, "end", text="2.1 Communication Parameters", open=True)
        l2_print_param = self.cas_tree.insert(l1_print, "end", text="2.2 Print Parameters", open=True)
        l2_pc_direct = self.cas_tree.insert(l1_print, "end", text="2.3 PC Direct Parameters", open=True)

        # --- LEVEL 3 SUB-BRANCHES ---
        l3_ambient = self.cas_tree.insert(l2_balance, "end", text="1.1.1 Installation Site / Ambient Conditions")
        l3_filter = self.cas_tree.insert(l2_balance, "end", text="1.1.2 Application Filter")
        l3_stability = self.cas_tree.insert(l2_balance, "end", text="1.1.3 Stability Range")
        l3_delay = self.cas_tree.insert(l2_balance, "end", text="1.1.4 Stability Delay")
        l3_taring = self.cas_tree.insert(l2_balance, "end", text="1.1.5 Taring Mode")
        l3_auto_z = self.cas_tree.insert(l2_balance, "end", text="1.1.6 Autozero Tracking")
        l3_unit = self.cas_tree.insert(l2_balance, "end", text="1.1.7 Weight Unit Selection")
        l3_accuracy = self.cas_tree.insert(l2_balance, "end", text="1.1.8 Display Accuracy / Resolution")
        l3_cal_func = self.cas_tree.insert(l2_balance, "end", text="1.1.9 Calibration & Adjustment Function")
        l3_process = self.cas_tree.insert(l2_balance, "end", text="1.1.10 Adjustment Process Execution")
        l3_zero = self.cas_tree.insert(l2_balance, "end", text="1.1.11 Zero Range Boundaries")
        l3_power_zero = self.cas_tree.insert(l2_balance, "end", text="1.1.12 Zero at Power-On Limit")
        l3_tare_zero_pwr = self.cas_tree.insert(l2_balance, "end", text="1.1.13 Tare/Zero at Power-on State")
        l3_output_rate = self.cas_tree.insert(l2_balance, "end", text="1.1.14 Transducer Output Data Rate")
        l3_isocal = self.cas_tree.insert(l2_balance, "end", text="1.1.15 Automated IsoCal Reminders")

        # --- LEVEL 4 TARGET RESOLUTIONS ---
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.1 Very stable conditions", values=("1.1.1", "1.1.1.1"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.2 Stable conditions [Factory O]", values=("1.1.1", "1.1.1.2"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.3 Unstable conditions", values=("1.1.1", "1.1.1.3"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.4 Very unstable conditions", values=("1.1.1", "1.1.1.4"))

        self.cas_tree.insert(l3_filter, "end", text="1.1.2.1 Final readout [Factory O]", values=("1.1.2", "1.1.2.1"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.2 Dosing mode", values=("1.1.2", "1.1.2.2"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.3 Reduced filter matrix", values=("1.1.2", "1.1.2.3"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.4 Filter pipeline off", values=("1.1.2", "1.1.2.4"))

        self.cas_tree.insert(l3_stability, "end", text="1.1.3.1 1/4 scale interval (Maximum accuracy)", values=("1.1.3", "1.1.3.1"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.2 1/2 scale interval (Very accurate)", values=("1.1.3", "1.1.3.2"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.3 1 scale interval (Accurate)", values=("1.1.3", "1.1.3.3"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.4 2 scale interval (Quick) [Factory O]", values=("1.1.3", "1.1.3.4"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.5 4 scale interval (Very quick)", values=("1.1.3", "1.1.3.5"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.6 8 scale interval (Very low)", values=("1.1.3", "1.1.3.6"))

        self.cas_tree.insert(l3_delay, "end", text="1.1.4.1 Very short", values=("1.1.4", "1.1.4.1"))
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.2 Short [Factory O]", values=("1.1.4", "1.1.4.2"))
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.3 Moderate", values=("1.1.4", "1.1.4.3"))
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.4 Long", values=("1.1.4", "1.1.4.4"))

        self.cas_tree.insert(l3_taring, "end", text="1.1.5.1 Without stability", values=("1.1.5", "1.1.5.1"))
        self.cas_tree.insert(l3_taring, "end", text="1.1.5.2 After stability [Factory O]", values=("1.1.5", "1.1.5.2"))

        self.cas_tree.insert(l3_auto_z, "end", text="1.1.6.1 ON [Factory O]", values=("1.1.6", "1.1.6.1"))
        self.cas_tree.insert(l3_auto_z, "end", text="1.1.6.2 OFF", values=("1.1.6", "1.1.6.2"))

        self.cas_tree.insert(l3_unit, "end", text="1.1.7.1 Available unit list", values=("1.1.7", "1.1.7.1"))
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.2 g, grams [Factory O]", values=("1.1.7", "1.1.7.2"))
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.3 Units: Kilogram to Newton", values=("1.1.7", "1.1.7.3"))

        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.1 All digits on [Factory O]", values=("1.1.8", "1.1.8.1"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.2 Last digit on/off during load change", values=("1.1.8", "1.1.8.2"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.3 Scale interval index +1", values=("1.1.8", "1.1.8.3"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.4 Scale interval index +2", values=("1.1.8", "1.1.8.4"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.5 Scale interval index +3", values=("1.1.8", "1.1.8.5"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.6 Last digit scale interval 1", values=("1.1.8", "1.1.8.6"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.7 Last digit off", values=("1.1.8", "1.1.8.7"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.14 10x resolution magnification", values=("1.1.8", "1.1.8.14"))

        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.1 Ext. adjustment with default weight [Factory O]", values=("1.1.9", "1.1.9.1"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.3 Ext. adjustment with user-defined weight", values=("1.1.9", "1.1.9.3"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.4 Internal adjustment*", values=("1.1.9", "1.1.9.4"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.6 Ext. linearization with default weights", values=("1.1.9", "1.1.9.6"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.7 Ext. linearization with user-defined weights", values=("1.1.9", "1.1.9.7"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.8 Set the preload", values=("1.1.9", "1.1.9.8"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.9 Delete the preload", values=("1.1.9", "1.1.9.9"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.10 Cal. key/command blocked", values=("1.1.9", "1.1.9.10"))

        self.cas_tree.insert(l3_process, "end", text="1.1.10.1 Adjust immediately [Factory O]", values=("1.1.10", "1.1.10.1"))
        self.cas_tree.insert(l3_process, "end", text="1.1.10.2 Calibration before adjustment", values=("1.1.10", "1.1.10.2"))

        self.cas_tree.insert(l3_zero, "end", text="1.1.11.2 2% of max load [Factory O]", values=("1.1.11", "1.1.11.2"))
        self.cas_tree.insert(l3_zero, "end", text="1.1.11.4 10% of max load", values=("1.1.11", "1.1.11.4"))

        self.cas_tree.insert(l3_power_zero, "end", text="1.1.12.4 10% of max load [Factory O]", values=("1.1.12", "1.1.12.4"))
        self.cas_tree.insert(l3_power_zero, "end", text="1.1.12.7 100% of max load", values=("1.1.12", "1.1.12.7"))

        self.cas_tree.insert(l3_tare_zero_pwr, "end", text="1.1.13.1 On [Factory O]", values=("1.1.13", "1.1.13.1"))
        self.cas_tree.insert(l3_tare_zero_pwr, "end", text="1.1.13.2 Off", values=("1.1.13", "1.1.13.2"))

        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.1 Normal [Factory O]", values=("1.1.14", "1.1.14.1"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.2 Fast", values=("1.1.14", "1.1.14.2"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.3 Slow, typ. 10 Hz", values=("1.1.14", "1.1.14.3"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.4 Moderate, typ. 20 Hz", values=("1.1.14", "1.1.14.4"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.5 Quick, typ. 25 Hz", values=("1.1.14", "1.1.14.5"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.6 Very quick, typ. 50 Hz", values=("1.1.14", "1.1.14.6"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.7 Maximum, typ. 100 Hz", values=("1.1.14", "1.1.14.7"))

        self.cas_tree.insert(l3_isocal, "end", text="1.1.15.1 Off [Factory O]", values=("1.1.15", "1.1.15.1"))
        self.cas_tree.insert(l3_isocal, "end", text="1.1.15.2 Note alerts active", values=("1.1.15", "1.1.15.2"))

        # --- LEVEL 3 BRANCHES (2.1 PRINT COMMUNICATION) ---
        l3_p_data = self.cas_tree.insert(l2_print_comm, "end", text="2.1.1 Data Output Trigger Mode")
        l3_p_can = self.cas_tree.insert(l2_print_comm, "end", text="2.1.2 Cancel Automatic Output Condition")
        l3_p_cyc = self.cas_tree.insert(l2_print_comm, "end", text="2.1.3 Cycle Automatic Output Threshold")
        l3_p_fmt = self.cas_tree.insert(l2_print_comm, "end", text="2.1.4 Text Data Stream Output Format")

        # --- LEVEL 4 LEAF NODES (2.1 PRINTING SETS MAPPED FROM 25.PDF) ---
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.1 Individual value without stability [Factory O]", values=("3.1.1", "3.1.1.1"))
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.2 Individual value after stability", values=("3.1.1", "3.1.1.2"))
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.4 Automatic, without stability", values=("3.1.1", "3.1.1.4"))
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.5 Automatic, after stability", values=("3.1.1", "3.1.1.5"))

        self.cas_tree.insert(l3_p_can, "end", text="3.1.2.1 Cancel not possible [Factory O]", values=("3.1.2", "3.1.2.1"))
        self.cas_tree.insert(l3_p_can, "end", text="3.1.2.2 Cancel via print command execution", values=("3.1.2", "3.1.2.2"))

        self.cas_tree.insert(l3_p_cyc, "end", text="3.1.3.1 Transmit every data value standard [Factory O]", values=("3.1.3", "3.1.3.1"))
        self.cas_tree.insert(l3_p_cyc, "end", text="3.1.3.2 Transmit every second data value frame", values=("3.1.3", "3.1.3.2"))

        self.cas_tree.insert(l3_p_fmt, "end", text="3.1.4.1 16 characters raw SBI format data block [Factory O]", values=("3.1.4", "3.1.4.1"))
        self.cas_tree.insert(l3_p_fmt, "end", text="3.1.4.2 22 characters with identification", values=("3.1.4", "3.1.4.2"))

        # --- LEVEL 3 BRANCHES (2.2 PRINT PARAMETERS) ---
        l3_p_trig = self.cas_tree.insert(l2_print_param, "end", text="2.2.1 Print Key / Action Command Trigger")
        l3_p_lfmt = self.cas_tree.insert(l2_print_param, "end", text="2.2.2 Printout Report Layout Format")
        l3_p_app = self.cas_tree.insert(l2_print_param, "end", text="2.2.3 Printout Application Parameters")
        l3_p_glp = self.cas_tree.insert(l2_print_param, "end", text="2.2.4 Printout GLP Quality Compliance Protocol")

        # --- LEVEL 4 LEAF NODES (2.2 REPORTING PROFILES DATA) ---
        self.cas_tree.insert(l3_p_trig, "end", text="3.2.1.1 Manual trigger, execute without stability", values=("3.2.1", "3.2.1.1"))
        self.cas_tree.insert(l3_p_trig, "end", text="3.2.1.2 Manual trigger, require stability lock [Factory O]", values=("3.2.1", "3.2.1.2"))
        self.cas_tree.insert(l3_p_trig, "end", text="3.2.1.6 Automatic stream output after load change delta", values=("3.2.1", "3.2.1.6"))

        self.cas_tree.insert(l3_p_lfmt, "end", text="3.2.2.2 Application metrics with text identification [Factory O]", values=("3.2.2", "3.2.2.2"))

        self.cas_tree.insert(l3_p_app, "end", text="3.2.3.1 Off", values=("3.2.3", "3.2.3.1"))
        self.cas_tree.insert(l3_p_app, "end", text="3.2.3.2 All parameters [Factory O]", values=("3.2.3", "3.2.3.2"))
        self.cas_tree.insert(l3_p_app, "end", text="3.2.3.3 Only main parameters", values=("3.2.3", "3.2.3.3"))

        self.cas_tree.insert(l3_p_glp, "end", text="3.2.4.1 Off [Factory O]", values=("3.2.4", "3.2.4.1"))
        self.cas_tree.insert(l3_p_glp, "end", text="3.2.4.2 Only after cal./adjustment", values=("3.2.4", "3.2.4.2"))
        self.cas_tree.insert(l3_p_glp, "end", text="3.2.4.3 Always on, with every manual print", values=("3.2.4", "3.2.4.3"))

        # --- LEVEL 3 BRANCHES (2.3 PC DIRECT PARAMETERS) ---
        l3_pc_sep = self.cas_tree.insert(l2_pc_direct, "end", text="2.3.1 Decimal Radix Character Separator")
        l3_pc_out = self.cas_tree.insert(l2_pc_direct, "end", text="2.3.2 Active Data Bus Output Format")

        # --- LEVEL 4 LEAF NODES (2.3 PC DIRECT CORES) ---
        self.cas_tree.insert(l3_pc_sep, "end", text="3.3.1.1 Point (.) Separator [Factory O]", values=("3.3.1", "3.3.1.1"))
        self.cas_tree.insert(l3_pc_sep, "end", text="3.3.1.2 Comma (,) Separator", values=("3.3.1", "3.3.1.2"))

        self.cas_tree.insert(l3_pc_out, "end", text="3.3.2.1 Text and numerical value [Factory O]", values=("3.3.2", "3.3.2.1"))
        self.cas_tree.insert(l3_pc_out, "end", text="3.3.2.2 Numerical value only", values=("3.3.2", "3.3.2.2"))

        # --- LEVEL 3 BRANCHES (1.9 GENERAL) ---
        l3_menu_reset = self.cas_tree.insert(l2_general, "end", text="1.9.1 Registry Factory Reset Protocols")
        self.cas_tree.insert(l3_menu_reset, "end", text="1.9.1.1 Yes, wipe registers and map factory defaults", values=("1.9.1", "1.9.1.1"))
        self.cas_tree.insert(l3_menu_reset, "end", text="1.9.1.2 No, preserve active working configs [Factory O]", values=("1.9.1", "1.9.1.2"))

        self.cas_tree.bind("<<TreeviewSelect>>", self._on_cas_menu_node_click)

    def _render_scrolling_control_ui(self, parent_frame):
        """Generates a comprehensive scrolling sub-canvas encapsulating all central hardware stations."""
        control_canvas = tk.Canvas(parent_frame, bg="#1E293B", bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=control_canvas.yview)
        
        scrollable_content = ttk.Frame(control_canvas, style="ScrollCard.TFrame", padding=15)
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all"))
        )
        
        # Keep width constrained inside container but allow internal content heights to slide seamlessly
        control_canvas.create_window((0, 0), window=scrollable_content, anchor="nw", width=380)
        control_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        control_canvas.pack(side="left", fill="both", expand=True)

        # Rendering hardware operations panels sequentially inside scroll canvas
        ttk.Label(scrollable_content, text="SYSTEM INITIALIZATION", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 5))
        power_row = ttk.Frame(scrollable_content, style="TFrame")
        power_row.pack(fill="x", pady=(0, 15))
        ttk.Button(power_row, text="START WEIGH CELL", style="Start.TButton", command=self.start_machine).pack(side="left")
        ttk.Button(power_row, text="STOP INTEL CIRCUIT", style="Stop.TButton", command=self.stop_machine).pack(side="left", padx=10)

        ttk.Label(scrollable_content, text="TRANSDUCER INGESTION ENGINE", style="CardTitleX.TLabel").pack(anchor="w")
        ingest_row = ttk.Frame(scrollable_content, style="TFrame")
        ingest_row.pack(fill="x", pady=(5, 15))
        ttk.Button(ingest_row, text="Import Log (.txt)", style="Action.TButton", command=self._import_sensor_log_file).pack(fill="x", pady=2)
        ttk.Button(ingest_row, text="Toggle Source Mode", style="Action.TButton", command=self._toggle_stream_source_mode).pack(fill="x", pady=2)
        ttk.Label(ingest_row, textvariable=self.stream_status_text, style="Metric.TLabel", foreground="#38BDF8").pack(anchor="w", pady=4)

        ttk.Label(scrollable_content, text="SIMULATED RECEPTOR PAN CONTROL", style="CardTitle.TLabel").pack(anchor="w")
        slider_row = ttk.Frame(scrollable_content, style="TFrame")
        slider_row.pack(fill="x", pady=(5, 15))
        
        self.load_slider = tk.Scale(
            slider_row, from_=0, to=8200, orient="horizontal", resolution=1,
            variable=self.load_var, bg="#1E293B", fg="#F8FAFC", troughcolor="#0F172A",
            activebackground="#38BDF8", highlightthickness=0, command=self._on_slider_adjustment
        )
        self.load_slider.pack(fill="x")
        
        preset_row = ttk.Frame(slider_row, style="TFrame")
        preset_row.pack(fill="x", pady=(4, 0))
        ttk.Button(preset_row, text="Inject 535g Ref", style="Action.TButton", command=lambda: self._inject_preset_load(535.0)).pack(side="left", expand=True, fill="x")
        ttk.Button(preset_row, text="Clear (0g)", style="Action.TButton", command=lambda: self._inject_preset_load(0.0)).pack(side="left", padx=6, expand=True, fill="x")
        
        self.load_lbl_hint = ttk.Label(slider_row, text="Targeted Mass: 120.0000 g", style="SubTitle.TLabel")
        self.load_lbl_hint.pack(anchor="w", pady=(4, 0))

        ttk.Label(scrollable_content, text="HARDWARE TRIMMING & CALIBRATION", style="CardTitle.TLabel").pack(anchor="w")
        cal_grid = ttk.Frame(scrollable_content, style="TFrame")
        cal_grid.pack(fill="x", pady=(5, 0))

        ttk.Label(cal_grid, text="Manual Scaling Multiplier factor", style="FieldLabel.TLabel").pack(anchor="w", pady=(4, 2))
        self.manual_scale_str = tk.StringVar(value="1.000000")
        self.entry_scale = ttk.Entry(cal_grid, textvariable=self.manual_scale_str, font=("Consolas", 10))
        self.entry_scale.pack(fill="x", pady=2)
        ttk.Button(cal_grid, text="Apply Scalar Factor", style="Action.TButton", command=self.apply_manual_scaling).pack(fill="x", pady=(0, 8))

        ttk.Label(cal_grid, text="Auto-Calibration Reference standard (g)", style="FieldLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.auto_ref_str = tk.StringVar(value="500.0")
        self.entry_ref = ttk.Entry(cal_grid, textvariable=self.auto_ref_str, font=("Consolas", 10))
        self.entry_ref.pack(fill="x", pady=2)
        ttk.Button(cal_grid, text="Compute Auto-Calibration Span", style="Action.TButton", command=self.execute_auto_scale).pack(fill="x", pady=(0, 12))

        ttk.Button(scrollable_content, text="Zero-Scale Base Position", style="Action.TButton", command=self.execute_zero_scaling).pack(fill="x", pady=2)
        ttk.Button(scrollable_content, text="Tare Container Offsets", style="Action.TButton", command=self.execute_tare).pack(fill="x", pady=2)
        ttk.Button(scrollable_content, text="Flush System Calibration Pipelines", style="Action.TButton", command=self.reset_entire_pipeline).pack(fill="x", pady=(2, 0))

    def _render_telemetry_ui(self, parent):
        ttk.Label(parent, text="METROLOGICAL TELEMETRY MONITOR HUD", style="CardTitle.TLabel").pack(anchor="w")

        # --- METROLOGICAL indicator LCD PANEL MAPPING ---
        display_housing = tk.Frame(parent, bg="#334155", padx=8, pady=8, relief="sunken", borderwidth=3)
        display_housing.pack(fill="x", pady=(10, 10))
        
        display_canvas = tk.Frame(display_housing, bg="#0F172A", highlightbackground="#1E293B", highlightthickness=1)
        display_canvas.pack(fill="x")
        tk.Label(display_canvas, text="SARTORIUS INDUSTRIAL WZB INDICATOR", bg="#0F172A", fg="#475569", font=("Segoe UI", 8, "bold")).pack(anchor="nw", padx=10, pady=(6, 0))
        
        self.display_label = tk.Label(
            display_canvas, textvariable=self.display_text, bg="#0F172A", fg="#22C55E",
            font=("Consolas", 32, "bold"), anchor="e", width=26, padx=16, pady=12
        )
        self.display_label.pack(fill="x")

        status_bar = ttk.Frame(parent, style="Card.TFrame")
        status_bar.pack(fill="x", pady=(0, 10))

        self.blinker_canvas = tk.Canvas(status_bar, width=22, height=22, bg="#1E293B", highlightthickness=0)
        self.blinker_canvas.pack(side="left", padx=(2, 0))
        self.blinker_node = self.blinker_canvas.create_oval(4, 4, 18, 18, fill="#64748B", outline="#334155")

        ttk.Label(status_bar, textvariable=self.status_text, style="Metric.TLabel").pack(side="left", padx=8)

        ttk.Label(parent, text="INSTRUMENTATION PIPELINE CRITICAL REGISTERS", style="CardTitle.TLabel").pack(anchor="w", pady=(6, 4))
        matrix_box = tk.Frame(parent, bg="#0F172A", highlightbackground="#334155", highlightthickness=1, padx=12, pady=10)
        matrix_box.pack(fill="x", pady=(0, 14))

        ttk.Label(matrix_box, textvariable=self.raw_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.scale_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.zero_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.tare_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.command_status_text, style="Metric.TLabel", background="#0F172A", foreground="#4ADE80").pack(anchor="w", pady=2)

        # Scrolled Terminal Window Core
        ttk.Label(parent, text="UNIVERSAL REMOTE TRANSCIEVER SERIAL BUS MONITOR", style="CardTitle.TLabel").pack(anchor="w", pady=(6, 4))
        
        terminal_container = tk.Frame(parent, bg="#0F172A", highlightbackground="#334155", highlightthickness=1)
        terminal_container.pack(fill="both", expand=True)
        
        term_scroll = tk.Scrollbar(terminal_container, orient="vertical")
        self.message = tk.Text(terminal_container, yscrollcommand=term_scroll.set, wrap="word", bg="#0F172A", fg="#94A3B8", insertbackground="#F8FAFC", relief="flat", font=("Consolas", 9))
        
        term_scroll.config(command=self.message.yview)
        term_scroll.pack(side="right", fill="y")
        self.message.pack(side="left", fill="both", expand=True)
        
        self.message.insert("end", "[CORE_BUS] Multi-Standard hardware serial physical driver links mapped successfully.\n")
        self.message.configure(state="disabled")

        command_box = ttk.Frame(parent, style="Card.TFrame")
        command_box.pack(fill="x", pady=(12, 0))
        
        self.protocol_mode = "xBPI"  
        mode_row = ttk.Frame(command_box, style="TFrame")
        mode_row.pack(fill="x", pady=(0, 4))
        self.lbl_mode_indicator = ttk.Label(mode_row, text="Active Protocol Decoder: SARTORIUS xBPI COMPILER LINK", font=("Segoe UI", 9, "bold"), foreground="#38BDF8")
        self.lbl_mode_indicator.pack(side="left")
        
        entry_row = ttk.Frame(command_box, style="TFrame")
        entry_row.pack(fill="x")
        self.command_var = tk.StringVar(value="04 01 09 1E 2C")  
        self.command_entry = ttk.Entry(entry_row, textvariable=self.command_var, font=("Consolas", 10))
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(entry_row, text="Transmit Frame", style="Action.TButton", command=self.send_command).pack(side="right")

    def _generate_live_signal(self):
        if self.is_file_stream_active and self.file_stream_buffer:
            raw_adc = self.file_stream_buffer[self.file_stream_index]
            self.file_stream_index = (self.file_stream_index + 1) % len(self.file_stream_buffer)
            source_weight = raw_adc * self.adc_reference_scale
        else:
            source_weight = self.simulated_load

        # Ambient Site Filter Limits (1.1.1)
        if self.active_env_filter == "1.1.1.1": noise_bound = 0.0018
        elif self.active_env_filter == "1.1.1.3": noise_bound = 0.0540
        elif self.active_env_filter == "1.1.1.4": noise_bound = 0.1450
        else: noise_bound = 0.0140
            
        environmental_noise = random.uniform(-noise_bound, noise_bound)
        if self.active_autozero == "1.1.6.1" and abs(source_weight) < 0.008:
            environmental_noise *= 0.1
            source_weight = 0.0

        vibration_drift = 0.0006 * self.noise_seed
        self.noise_seed = (self.noise_seed + 0.5) % 500.0
        raw_signal_output = source_weight + environmental_noise + vibration_drift
        
        # Moving Average Array Depth (1.1.2)
        if self.active_app_filter == "1.1.2.1": filter_window_size = 20
        elif self.active_app_filter == "1.1.2.2": filter_window_size = 8
        elif self.active_app_filter == "1.1.2.3": filter_window_size = 4
        else: filter_window_size = 1
            
        self.filter_history_buffer.append(raw_signal_output)
        if len(self.filter_history_buffer) > filter_window_size:
            self.filter_history_buffer.pop(0)
            
        return sum(self.filter_history_buffer) / len(self.filter_history_buffer)

    def _process_calibrated_weight(self, source_signal):
        raw_calculated = ((source_signal - self.zero_reference) * self.scale_factor) - self.tare_offset
        if self.active_weight_unit == "1.1.7.3":
            return raw_calculated / 1000.0
        return raw_calculated

    def _evaluate_measurement_stability(self, weight_input):
        self.previous_weights_history.append(weight_input)
        if len(self.previous_weights_history) > 5:
            self.previous_weights_history.pop(0)
        max_delta = max(self.previous_weights_history) - min(self.previous_weights_history)
        
        threshold_mappings = {
            "1.1.3.1": 0.0025, "1.1.3.2": 0.0050, "1.1.3.3": 0.0100, "1.1.3.4": 0.0200, "1.1.3.5": 0.0400, "1.1.3.6": 0.0800
        }
        allowed_threshold = threshold_mappings.get(self.active_stability_range, 0.0200)
        self.is_currently_stable = max_delta <= allowed_threshold

    def _simulation_engine_tick(self):
        if self.machine_running:
            if not self.is_file_stream_active:
                self.simulated_load += (self.target_load - self.simulated_load) * 0.12
            
            raw_signal = self._generate_live_signal()
            transformed_net_weight = self._process_calibrated_weight(raw_signal)
            self.last_display_value = transformed_net_weight
            self._evaluate_measurement_stability(transformed_net_weight)
            stability_flag = " " if self.is_currently_stable else " [UNSTABLE]"
            
            unit_label = " kg" if self.active_weight_unit == "1.1.7.3" else " g"
            
            if self.active_accuracy_digits == "1.1.8.7": display_string_output = f"{transformed_net_weight:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.3": display_string_output = f"{transformed_net_weight:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.4": display_string_output = f"{transformed_net_weight:,.2f}"
            elif self.active_accuracy_digits == "1.1.8.5": display_string_output = f"{transformed_net_weight:,.1f}"
            elif self.active_accuracy_digits == "1.1.8.14": display_string_output = f"{transformed_net_weight:,.5f}"
            else: display_string_output = f"{transformed_net_weight:,.4f}"
                
            # --- CAS BEHAVIOR MAP: PC Direct Parameter Logics (2.3) ---
            if self.pc_output_format == "3.3.2.2":
                final_display_frame = f"{display_string_output}{stability_flag}"
            else:
                final_display_frame = f"{display_string_output}{unit_label}{stability_flag}"

            if self.pc_decimal_separator == "3.3.1.2":
                final_display_frame = final_display_frame.replace(".", ",")

            self.display_text.set(final_display_frame)
            self.raw_text.set(f"Transducer Input: {raw_signal:,.4f} g")
            
            if self.adjustment_state == "external adjustment": self.status_text.set("CAL.EXT" if not self.blink_on else "CALRUN")
            elif self.adjustment_state == "internal calibration": self.status_text.set("CAL.INT" if not self.blink_on else "CALRUN")
            else: self.status_text.set("EMULATOR BUS CORE: ONLINE" if not self.blink_on else "EMULATOR BUS CORE: TRANSCEIVER SCANS ACTIVE")
        else:
            self.display_text.set("------")
            self.raw_text.set(f"Transducer Input: {self.simulated_load:,.4f} g")

        try:
            self._scheduled_engine_loop_id = self.after(self.simulation_tick_rate_ms, self._simulation_engine_tick)
        except: pass

    def _status_blinker_tick(self):
        if self.machine_running:
            self.blink_on = not self.blink_on
            fill_color = "#22C55E" if self.blink_on else "#166534"
            self.blinker_canvas.itemconfig(self.blinker_node, fill=fill_color, outline="#4ADE80" if self.blink_on else "#14532D")
        else:
            self.blinker_canvas.itemconfig(self.blinker_node, fill="#64748B", outline="#334155")
        try: self.after(350, self._status_blinker_tick)
        except: pass

    def _on_safe_close(self):
        self.machine_running = False
        try: self.after_cancel(self._scheduled_engine_loop_id)
        except: pass
        self.destroy()


if __name__ == "__main__":
    app = ModernWeighCellSimulator()
    app.mainloop()