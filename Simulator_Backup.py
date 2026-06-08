import random
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class ModernWeighCellSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sartorius WZB Series - Virtual Weigh Cell Environment")
        self.geometry("1340x840")
        self.minsize(1200, 780)
        
        # 1. Core State Variables & Configurations
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
        
        # --- CAS CONFIGURATION SUITE STATE REGISTERS ---
        # 1.1 Balance Parameters
        self.active_env_filter = "1.1.1.2"        # Factory Default: Stable conditions
        self.active_app_filter = "1.1.2.1"        # Factory Default: Final readout
        self.active_stability_range = "1.1.3.4"   # Factory Default: 2 scale interval
        self.active_stability_delay = "1.1.4.2"   # Factory Default: Short
        self.active_taring_mode = "1.1.5.2"       # Factory Default: After stability
        self.active_autozero = "1.1.6.1"          # Factory Default: ON
        self.active_weight_unit = "1.1.7.2"       # Factory Default: g (grams)
        self.active_accuracy_digits = "1.1.8.1"   # Factory Default: All digits on
        self.active_cal_func = "1.1.9.1"          # Factory Default: Ext. adjust default weight
        self.active_adjust_process = "1.1.10.1"   # Factory Default: Adjust immediately
        self.active_zero_range = "1.1.11.2"       # Factory Default: 2% of max load
        self.active_poweron_zero = "1.1.12.4"     # Factory Default: 10% of max load
        self.active_poweron_tarezero = "1.1.13.1" # Factory Default: On
        self.active_output_rate = "1.1.14.1"      # Factory Default: Normal
        self.active_isocal = "1.1.15.1"           # Factory Default: Off
        
        # 1.9 General Settings Parameters
        self.active_menu_reset = "1.9.1.2"        # Factory Default: No, stand-by

        # Core Digital Signal Processing Filter Arrays & Trackers
        self.filter_history_buffer = []
        self.is_currently_stable = True
        self.previous_weights_history = [0.0] * 5
        self.simulation_tick_rate_ms = 50         # Controlled dynamically by 1.1.14.x
        
        # Sensor Log File Stream Buffers
        self.file_stream_buffer = []
        self.file_stream_index = 0
        self.is_file_stream_active = False
        self.loaded_file_path = ""
        
        # Calibration Reference Constant Mapping (Based on 535g Transducer Characteristics)
        self.adc_reference_scale = 535.0 / 44347000.0  
        
        # Command Bus Buffers & Transceiver Registers
        self.command_history = []
        self.xbpi_address = 0x00
        
        # 2. Dynamic UI Tracking Variables
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
        self._scheduled_engine_loop_id = self.after(self.simulation_tick_rate_ms, self._simulation_engine_tick)
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
        workspace.columnconfigure(0, weight=4)  # Expanded for comprehensive nesting trees
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
        """Constructs an exhaustive multi-level parameter hierarchy mimicking the CAS software system."""
        ttk.Label(parent, text="CAS CONFIGURATION SUITE", style="CardTitleX.TLabel").pack(anchor="w", pady=(0, 10))
        
        tree_scroll = ttk.Scrollbar(parent, orient="vertical")
        tree_scroll.pack(side="right", fill="y")
        
        self.cas_tree = ttk.Treeview(parent, yscrollcommand=tree_scroll.set, selectmode="browse")
        self.cas_tree.pack(fill="both", expand=True)
        tree_scroll.config(command=self.cas_tree.yview)
        
        self.cas_tree.heading("#0", text="Device Configuration Parameter List", anchor="w")

        # --- LEVEL 1 INITIAL ARCHITECTURE ---
        l1_setup = self.cas_tree.insert("", "end", text="1. Active Setup Menu", open=True)
        l1_print = self.cas_tree.insert("", "end", text="2. Active Print Menu")
        l1_device = self.cas_tree.insert("", "end", text="3. Active Device Menu")
        l1_app = self.cas_tree.insert("", "end", text="4. Active Application Menu")

        self.cas_tree.insert(l1_print, "end", text="Print Options Configuration Blocked")
        self.cas_tree.insert(l1_device, "end", text="Device Interface Mapping Blocked")
        self.cas_tree.insert(l1_app, "end", text="Application Control Registers Blocked")

        # --- LEVEL 2 INITIAL ARCHITECTURE ---
        l2_balance = self.cas_tree.insert(l1_setup, "end", text="1.1 Balance Settings", open=True)
        l2_general = self.cas_tree.insert(l1_setup, "end", text="1.9 General Settings", open=True)

        # --- LEVEL 3 BALANCE NESTINGS (1.1) ---
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

        # --- LEVEL 4 LEAF PARAMETERS (1.1 BALANCE SETTINGS OPTIONS) ---
        # 1.1.1 Installation Site Settings
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.1 Very stable conditions", values=("1.1.1", "1.1.1.1"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.2 Stable conditions [Factory O]", values=("1.1.1", "1.1.1.2"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.3 Unstable conditions", values=("1.1.1", "1.1.1.3"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.4 Very unstable conditions", values=("1.1.1", "1.1.1.4"))

        # 1.1.2 Application Filter Settings
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.1 Final readout [Factory O]", values=("1.1.2", "1.1.2.1"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.2 Dosing mode", values=("1.1.2", "1.1.2.2"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.3 Reduced filter matrix", values=("1.1.2", "1.1.2.3"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.4 Filter pipeline off", values=("1.1.2", "1.1.2.4"))

        # 1.1.3 Stability Range Boundaries
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.1 1/4 scale interval (Max Accuracy)", values=("1.1.3", "1.1.3.1"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.2 1/2 scale interval (Very Accurate)", values=("1.1.3", "1.1.3.2"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.3 1 scale interval (Accurate)", values=("1.1.3", "1.1.3.3"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.4 2 scale interval (Quick execution) [Factory O]", values=("1.1.3", "1.1.3.4"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.5 4 scale interval (Very Quick)", values=("1.1.3", "1.1.3.5"))
        self.cas_tree.insert(l3_stability, "end", text="1.1.3.6 8 scale interval (Very Low stability definition)", values=("1.1.3", "1.1.3.6"))

        # 1.1.4 Stability Delay Channels
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.1 Very short latch window", values=("1.1.4", "1.1.4.1"))
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.2 Short latch window [Factory O]", values=("1.1.4", "1.1.4.2"))
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.3 Moderate latch window", values=("1.1.4", "1.1.4.3"))
        self.cas_tree.insert(l3_delay, "end", text="1.1.4.4 Long latch window", values=("1.1.4", "1.1.4.4"))

        # 1.1.5 Taring Mode
        self.cas_tree.insert(l3_taring, "end", text="1.1.5.1 Without stability checkpoint", values=("1.1.5", "1.1.5.1"))
        self.cas_tree.insert(l3_taring, "end", text="1.1.5.2 After stability confirmation [Factory O]", values=("1.1.5", "1.1.5.2"))

        # 1.1.6 Autozero Dynamic Tracking
        self.cas_tree.insert(l3_auto_z, "end", text="1.1.6.1 Autozero active [Factory O]", values=("1.1.6", "1.1.6.1"))
        self.cas_tree.insert(l3_auto_z, "end", text="1.1.6.2 Autozero off", values=("1.1.6", "1.1.6.2"))

        # 1.1.7 Weight Unit Selection Metrics
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.1 View available unit profiles", values=("1.1.7", "1.1.7.1"))
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.2 Grams (g) engineering base [Factory O]", values=("1.1.7", "1.1.7.2"))
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.3 Extended metrics matrix (Kilogram to Newton)", values=("1.1.7", "1.1.7.3"))

        # 1.1.8 Display Accuracy / Multipliers
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.1 All fractional digits active [Factory O]", values=("1.1.8", "1.1.8.1"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.2 Toggle last digit during load transitions", values=("1.1.8", "1.1.8.2"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.3 Scale interval step index +1", values=("1.1.8", "1.1.8.3"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.4 Scale interval step index +2", values=("1.1.8", "1.1.8.4"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.5 Scale interval step index +3", values=("1.1.8", "1.1.8.5"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.6 Force last element value to 1", values=("1.1.8", "1.1.8.6"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.7 Deactivate trailing fraction element", values=("1.1.8", "1.1.8.7"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.14 Magnify 10x resolution data parameters", values=("1.1.8", "1.1.8.14"))

        # 1.1.9 Calibration & Adjustment Settings
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.1 External adjustment (Default Mass) [Factory O]", values=("1.1.9", "1.1.9.1"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.3 External adjustment (Custom Weight)", values=("1.1.9", "1.1.9.3"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.4 Internal alignment loop (*NC Variants Only)", values=("1.1.9", "1.1.9.4"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.6 External linearization (Default Balance Masses)", values=("1.1.9", "1.1.9.6"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.7 External linearization (User Calibration weights)", values=("1.1.9", "1.1.9.7"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.8 Capture current structural preload standard", values=("1.1.9", "1.1.9.8"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.9 Erase defined load pre-allocation matrices", values=("1.1.9", "1.1.9.9"))
        self.cas_tree.insert(l3_cal_func, "end", text="1.1.9.10 Block local hardware keys/commands", values=("1.1.9", "1.1.9.10"))

        # 1.1.10 Adjustment Processes
        self.cas_tree.insert(l3_process, "end", text="1.1.10.1 Execute adjustment cycle immediately [Factory O]", values=("1.1.10", "1.1.10.1"))
        self.cas_tree.insert(l3_process, "end", text="1.1.10.2 Require baseline calibration run first", values=("1.1.10", "1.1.10.2"))

        # 1.1.11 Zero Tracking Ranges
        self.cas_tree.insert(l3_zero, "end", text="1.1.11.2 Maximum span bounded to 2% Max Load [Factory O]", values=("1.1.11", "1.1.11.2"))
        self.cas_tree.insert(l3_zero, "end", text="1.1.11.4 Maximum span bounded to 10% Max Load", values=("1.1.11", "1.1.11.4"))

        # 1.1.12 Power-On Zero Thresholds
        self.cas_tree.insert(l3_power_zero, "end", text="1.1.12.4 Bound initialization offset to 10% [Factory O]", values=("1.1.12", "1.1.12.4"))
        self.cas_tree.insert(l3_power_zero, "end", text="1.1.12.7 Bound initialization offset to 100% capacity", values=("1.1.12", "1.1.12.7"))

        # 1.1.13 Tare/Zero state at power on
        self.cas_tree.insert(l3_tare_zero_pwr, "end", text="1.1.13.1 Clear registers at initialization [Factory O]", values=("1.1.13", "1.1.13.1"))
        self.cas_tree.insert(l3_tare_zero_pwr, "end", text="1.1.13.2 Preserve previous persistent state profiles", values=("1.1.13", "1.1.13.2"))

        # 1.1.14 Output rate / Clock tracking delays
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.1 Standard metrological tracking rate [Factory O]", values=("1.1.14", "1.1.14.1"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.2 High priority update line", values=("1.1.14", "1.1.14.2"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.3 Low speed asynchronous clock (10 Hz / 100ms)", values=("1.1.14", "1.1.14.3"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.4 Balanced precision clock line (20 Hz / 50ms)", values=("1.1.14", "1.1.14.4"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.5 Automated manufacturing speed track (25 Hz / 40ms)", values=("1.1.14", "1.1.14.5"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.6 High-speed sensor transceiver rate (50 Hz / 20ms)", values=("1.1.14", "1.1.14.6"))
        self.cas_tree.insert(l3_output_rate, "end", text="1.1.14.7 Full telemetry raw data throughput (100 Hz / 10ms)", values=("1.1.14", "1.1.14.7"))

        # 1.1.15 IsoCal Core Settings
        self.cas_tree.insert(l3_isocal, "end", text="1.1.15.1 Suppress automated warnings [Factory O]", values=("1.1.15", "1.1.15.1"))
        self.cas_tree.insert(l3_isocal, "end", text="1.1.15.2 Append protocol notice alerts", values=("1.1.15", "1.1.15.2"))

        # --- LEVEL 3 GENERAL NESTINGS (1.9) ---
        l3_menu_reset = self.cas_tree.insert(l2_general, "end", text="1.9.1 Configuration Architecture Factory Reset Options")

        # --- LEVEL 4 LEAF PARAMETERS (1.9 GENERAL SETTINGS OPTIONS) ---
        self.cas_tree.insert(l3_menu_reset, "end", text="1.9.1.1 Yes, flush settings and load factory standard", values=("1.9.1", "1.9.1.1"))
        self.cas_tree.insert(l3_menu_reset, "end", text="1.9.1.2 No, preserve standby registers [Factory O]", values=("1.9.1", "1.9.1.2"))

        self.cas_tree.bind("<<TreeviewSelect>>", self._on_cas_menu_node_click)

    def _on_cas_menu_node_click(self, event):
        selected_node = self.cas_tree.selection()
        if not selected_node:
            return
            
        node_data = self.cas_tree.item(selected_node[0])
        node_values = node_data.get("values", "")
        
        if node_values:
            param_group, target_code = node_values[0], node_values[1]
            
            # Dynamic state switching based on parameter paths
            if param_group == "1.1.1":
                self.active_env_filter = target_code
                self._write_terminal_log(f"[CAS SUITE] Ambient site configuration reassigned -> Code: {target_code}")
            elif param_group == "1.1.2":
                self.active_app_filter = target_code
                self.filter_history_buffer.clear()
                self._write_terminal_log(f"[CAS SUITE] Digital moving-average window length modified -> Code: {target_code}")
            elif param_group == "1.1.3":
                self.active_stability_range = target_code
                self._write_terminal_log(f"[CAS SUITE] Verification variance window updated -> Code: {target_code}")
            elif param_group == "1.1.4":
                self.active_stability_delay = target_code
                self._write_terminal_log(f"[CAS SUITE] Transient delay confirmation track -> Code: {target_code}")
            elif param_group == "1.1.5":
                self.active_taring_mode = target_code
                self._write_terminal_log(f"[CAS SUITE] Taring synchronization interlock mode -> Code: {target_code}")
            elif param_group == "1.1.6":
                self.active_autozero = target_code
                self._write_terminal_log(f"[CAS SUITE] Dynamic zero drift auto-tracking baseline -> Code: {target_code}")
            elif param_group == "1.1.7":
                self.active_weight_unit = target_code
                self._write_terminal_log(f"[CAS SUITE] Target legal metrology legal unit set -> Code: {target_code}")
            elif param_group == "1.1.8":
                self.active_accuracy_digits = target_code
                self._write_terminal_log(f"[CAS SUITE] Screen scaling multiplier formatting profile -> Code: {target_code}")
            elif param_group == "1.1.9":
                self.active_cal_func = target_code
                self._write_terminal_log(f"[CAS SUITE] Primary calibration function route updated -> Code: {target_code}")
                if target_code == "1.1.9.10":
                    self._write_terminal_log("[SECURITY WARNING] Remote hardware interface key control lines are now BLOCKED.")
            elif param_group == "1.1.10":
                self.active_adjust_process = target_code
                self._write_terminal_log(f"[CAS SUITE] Execution sequence protocol model -> Code: {target_code}")
            elif param_group == "1.1.11":
                self.active_zero_range = target_code
                self._write_terminal_log(f"[CAS SUITE] Local balance threshold zero capacity span -> Code: {target_code}")
            elif param_group == "1.1.12":
                self.active_poweron_zero = target_code
                self._write_terminal_log(f"[CAS SUITE] Initial cold-start calibration limit bound -> Code: {target_code}")
            elif param_group == "1.1.13":
                self.active_poweron_tarezero = target_code
                self._write_terminal_log(f"[CAS SUITE] Power-on register clean matrix -> Code: {target_code}")
            elif param_group == "1.1.14":
                self.active_output_rate = target_code
                self._reconfigure_asynchronous_clock_intervals(target_code)
            elif param_group == "1.1.15":
                self.active_isocal = target_code
                self._write_terminal_log(f"[CAS SUITE] IsoCal internal software compliance tracker -> Code: {target_code}")
            elif param_group == "1.1.9" or param_group == "2.1.9" or param_group == "3.1.9":
                self._write_terminal_log(f"[CAS SUITE] Calibration definition path override -> Code: {target_code}")
                
            # --- 1.9.1.1 FULL FACTORY REBOOT PIPELINE IMPL ---
            elif param_group == "1.9.1":
                if target_code == "1.9.1.1":
                    self._execute_factory_menu_reset()
                else:
                    self.active_menu_reset = "1.9.1.2"
                    
            self._set_command_status(f"LATCH PARAM CODE: {target_code}")

    def _reconfigure_asynchronous_clock_intervals(self, code):
        """Alters the main physical layer polling loop frequency based on manual data rate specifications."""
        rate_mappings = {
            "1.1.14.1": 50,   # Normal baseline configuration tracking frequency (20 Hz)
            "1.1.14.2": 40,   # High priority line response (25 Hz)
            "1.1.14.3": 100,  # Slow operational line tracker (10 Hz)
            "1.1.14.4": 50,   # Balanced tracking line output (20 Hz)
            "1.1.14.5": 40,   # High speed manufacturing line output (25 Hz)
            "1.1.14.6": 20,   # High performance pipeline tracking loop (50 Hz)
            "1.1.14.7": 10,   # Real-time raw maximum processor bandwidth loop (100 Hz)
        }
        self.simulation_tick_rate_ms = rate_mappings.get(code, 50)
        self._write_terminal_log(f"[HARDWARE CLOCK] System sampling tick interval modified to: {self.simulation_tick_rate_ms}ms ({1000//self.simulation_tick_rate_ms} Hz)")

    def _execute_factory_menu_reset(self):
        """Flushes all volatile registers back to original manual factory parameters."""
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
        self.active_menu_reset = "1.9.1.2"
        
        self.simulation_tick_rate_ms = 50
        self.filter_history_buffer.clear()
        self.reset_entire_pipeline()
        
        self._write_terminal_log("[FACTORY RESET] Clear memory frame complete. All registry indices returned to Factory parameters (O).")
        messagebox.showinfo("Factory Reset", "CAS Registry reset successfully execution completed. All hardware registers re-aligned to factory specifications.")

    def _render_telemetry_ui(self, parent):
        ttk.Label(parent, text="METROLOGICAL REAL-TIME READOUT", style="CardTitle.TLabel").pack(anchor="w")

        display_canvas = tk.Frame(parent, bg="#06090E", highlightbackground="#222A3A", highlightthickness=1)
        display_canvas.pack(fill="x", pady=(10, 10))

        unit_overlay = tk.Label(display_canvas, text="NET WT", bg="#06090E", fg="#4A5568", font=("Segoe UI", 9, "bold"))
        unit_overlay.pack(anchor="nw", padx=12, pady=(8, 0))

        self.display_label = tk.Label(
            display_canvas, textvariable=self.display_text, bg="#06090E", fg="#00E5FF",
            font=("Consolas", 32, "bold"), anchor="e", padx=16, pady=8
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
        """Generates raw transducer metric steps based on ambient environment variations."""
        if self.is_file_stream_active and self.file_stream_buffer:
            raw_adc = self.file_stream_buffer[self.file_stream_index]
            self.file_stream_index = (self.file_stream_index + 1) % len(self.file_stream_buffer)
            source_weight = raw_adc * self.adc_reference_scale
        else:
            source_weight = self.simulated_load

        # --- CAS BEHAVIORAL MAP: 1.1.1 Site Variation Profiles ---
        if self.active_env_filter == "1.1.1.1":   # Very stable conditions
            noise_bound = 0.0018
        elif self.active_env_filter == "1.1.1.3": # Unstable conditions
            noise_bound = 0.0540
        elif self.active_env_filter == "1.1.1.4": # Very unstable conditions
            noise_bound = 0.1450
        else:                                     # 1.1.1.2 Stable conditions (O)
            noise_bound = 0.0140
            
        environmental_noise = random.uniform(-noise_bound, noise_bound)
        
        # Implement Autozero logic (1.1.6) if weight drifts extremely close to absolute origin
        if self.active_autozero == "1.1.6.1" and abs(source_weight) < 0.008:
            environmental_noise *= 0.1
            source_weight = 0.0

        vibration_drift = 0.0006 * self.noise_seed
        self.noise_seed = (self.noise_seed + 0.5) % 500.0
        
        raw_signal_output = source_weight + environmental_noise + vibration_drift
        
        # --- CAS BEHAVIORAL MAP: 1.1.2 Moving Average Window Multipliers ---
        if self.active_app_filter == "1.1.2.1":   # Final readout (O)
            filter_window_size = 20
        elif self.active_app_filter == "1.1.2.2": # Dosing
            filter_window_size = 8
        elif self.active_app_filter == "1.1.2.3": # Reduced filter matrix
            filter_window_size = 4
        else:                                     # 1.1.2.4 Filter off
            filter_window_size = 1
            
        self.filter_history_buffer.append(raw_signal_output)
        if len(self.filter_history_buffer) > filter_window_size:
            self.filter_history_buffer.pop(0)
            
        return sum(self.filter_history_buffer) / len(self.filter_history_buffer)

    def _process_calibrated_weight(self, source_signal):
        raw_calulated = ((source_signal - self.zero_reference) * self.scale_factor) - self.tare_offset
        
        # --- CAS BEHAVIORAL MAP: 1.1.7 Weight Unit Translation ---
        if self.active_weight_unit == "1.1.7.3":
            # Map conversion coordinates to approximate an alternative unit (e.g. Kilograms)
            return raw_calulated / 1000.0
        return raw_calulated

    def _evaluate_measurement_stability(self, weight_input):
        """Monitors system variance to flag parameter tracking parameters."""
        self.previous_weights_history.append(weight_input)
        if len(self.previous_weights_history) > 5:
            self.previous_weights_history.pop(0)
            
        max_delta = max(self.previous_weights_history) - min(self.previous_weights_history)
        
        # --- CAS BEHAVIORAL MAP: 1.1.3 Allowed stability deviation spans ---
        threshold_mappings = {
            "1.1.3.1": 0.0025,  # 1/4 scale interval
            "1.1.3.2": 0.0050,  # 1/2 scale interval
            "1.1.3.3": 0.0100,  # 1 scale interval
            "1.1.3.4": 0.0200,  # 2 scale interval (O)
            "1.1.3.5": 0.0400,  # 4 scale interval
            "1.1.3.6": 0.0800,  # 8 scale interval
        }
        allowed_threshold = threshold_mappings.get(self.active_stability_range, 0.0200)
        self.is_currently_stable = max_delta <= allowed_threshold

    def start_machine(self):
        if self.machine_running:
            return
        
        # --- CAS BEHAVIORAL MAP: 1.1.13 Configuration power checks ---
        if self.active_poweron_tarezero == "1.1.13.1":
            self.zero_reference = 0.0
            self.tare_offset = 0.0
            self.zero_text.set("Zero Ref   : 0.0000 g")
            self.tare_text.set("Tare Base  : 0.0000 g")
            
        self.machine_running = True
        self.status_text.set("ONLINE | METROLOGY RUNNING")
        self._write_terminal_log("[SYSTEM] Metrological data transceiver stream loop active.")

    def stop_machine(self):
        if not self.machine_running:
            return
        self.machine_running = False
        self.blink_on = False
        self.status_text.set("SYSTEM OFFLINE")
        self.blinker_canvas.itemconfig(self.blinker_node, fill="#2D3748", outline="#1A202C")
        self.display_text.set("OFFLINE")
        self._write_terminal_log("[SYSTEM] Metrological data transceiver stream loop paused.")

    def apply_manual_scaling(self):
        # Prevent actions if command interfaces are completely blocked via 1.1.9.10
        if self.active_cal_func == "1.1.9.10":
            messagebox.showerror("Access Blocked", "Metrological parameters are currently BLOCKED (Code 1.1.9.10).")
            return
        try:
            factor = float(self.manual_scale_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid numerical matrix parameters format.")
            return
        if factor <= 0:
            messagebox.showerror("Range Fault", "Scaling configurations must map above analytical limits.")
            return
        self.scale_factor = factor
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._write_terminal_log(f"[CAL] Custom multiplier scalar stored: {self.scale_factor:.6f}")

    def execute_zero_scaling(self):
        if self.active_cal_func == "1.1.9.10":
            self._write_terminal_log("[SECURITY] Blocked Zero-scale action attempt.")
            return
            
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        
        # --- CAS BEHAVIORAL MAP: 1.1.11 Maximum zero tracking boundary thresholds ---
        max_allowed_zero = 820.0 if self.active_zero_range == "1.1.11.4" else 164.0  # 10% vs 2% of standard system threshold parameters
        if abs(current_raw) > max_allowed_zero:
            messagebox.showerror("Zero Balancing Fault", f"Transducer drift points exceed maximum allowed configuration rules limits ({self.active_zero_range}).")
            return
            
        self.zero_reference = current_raw
        self.zero_text.set(f"Zero Ref   : {self.zero_reference:,.4f} g")
        self._write_terminal_log(f"[CAL] Zero baseline snapshot captured: {self.zero_reference:,.4f} g")

    def execute_tare(self):
        if self.active_cal_func == "1.1.9.10": return
        
        # --- CAS BEHAVIORAL MAP: 1.1.5 Stability Latch Interlocks ---
        if self.active_taring_mode == "1.1.5.2" and not self.is_currently_stable:
            self._write_terminal_log("[TARE ABORTED] Pipeline verification delayed: waiting for data signal line stability.")
            messagebox.showwarning("Metrological Lock", "Cannot capture tare value while signal fluctuations exceed active stability limits.")
            return
            
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.tare_offset = self._process_calibrated_weight(current_raw)
        self.tare_text.set(f"Tare Base  : {self.tare_offset:,.4f} g")
        self._write_terminal_log(f"[CAL] Container envelope offsets synchronized: {self.tare_offset:,.4f} g")

    def execute_auto_scale(self):
        if self.active_cal_func == "1.1.9.10": return
        try:
            reference_weight = float(self.auto_ref_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid calibration mass format.")
            return
        if reference_weight <= 0: return

        sample_raw = self._generate_live_signal() if self.machine_running else max(self.simulated_load, 0.001)
        delta_span = sample_raw - self.zero_reference
        if abs(delta_span) < 1e-5: return

        self.scale_factor = reference_weight / delta_span
        self.manual_scale_str.set(f"{self.scale_factor:.6f}")
        self.scale_text.set(f"Multiplier : {self.scale_factor:.6f}")
        self._write_terminal_log(f"[CAL] Internal span linear regression re-scaled against weight standard: {reference_weight:.4f} g")

    def reset_entire_pipeline(self):
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Multiplier : 1.000000")
        self.zero_text.set("Zero Ref   : 0.0000 g")
        self.tare_text.set("Tare Base  : 0.0000 g")

    def _import_sensor_log_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not file_path: return
        try:
            temp_buffer = []
            with open(file_path, "r") as f:
                for line in f:
                    cleaned = line.strip()
                    if cleaned.startswith("ADC:"):
                        try:
                            temp_buffer.append(float(cleaned.split(":")[1]))
                        except: continue
            if not temp_buffer: return
            self.file_stream_buffer = temp_buffer
            self.file_stream_index = 0
            self.loaded_file_path = os.path.basename(file_path)
            self.is_file_stream_active = True
            self.stream_status_text.set(f"DATA STREAM: {self.loaded_file_path}")
            self._write_terminal_log(f"[INGEST] Buffered {len(self.file_stream_buffer)} hardware registers from dataset log.")
        except Exception as e:
            messagebox.showerror("I/O Error", str(e))

    def _toggle_stream_source_mode(self):
        if not self.file_stream_buffer: return
        self.is_file_stream_active = not self.is_file_stream_active
        self.stream_status_text.set(f"DATA STREAM: {self.loaded_file_path}" if self.is_file_stream_active else "DATA STREAM: MANUAL MODE")

    def send_command(self):
        raw_input = self.command_var.get().strip()
        if not raw_input: return
        if raw_input.upper().startswith("ESC") or len(raw_input.split()) == 0 or not all(c in "0123456789ABCDEFabcdef " for c in raw_input):
            self.protocol_mode = "RS232/SBI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: LEGACY RS232-SBI MODE", foreground="#FF3D71")
            tx_frame = self._process_legacy_rs232_ascii(raw_input.upper())
            self._write_terminal_log(f"[RS232 RX] ASCII -> '{raw_input}' | [TX] -> {tx_frame}")
        else:
            self.protocol_mode = "xBPI"
            self.lbl_mode_indicator.config(text="Active Protocol Decoder: SARTORIUS xBPI COMPILER MODE", foreground="#00E676")
            try:
                byte_array = bytes.fromhex(raw_input)
                tx_bytes = self._process_binary_xbpi_frame(byte_array)
                tx_hex_string = " ".join(f"{b:02X}" for b in tx_bytes)
                self._write_terminal_log(f"[xBPI RX] Binary Frame -> {raw_input} | [TX] -> {tx_hex_string}")
            except: pass

    def _process_binary_xbpi_frame(self, data: bytes) -> bytes:
        if len(data) < 3 or len(data) != data[0] + 1 or sum(data[:-1]) % 256 != data[-1]: 
            return bytes([0x03, 0x41, 0x92])  
        function_number = data[3] if len(data) > 3 else 0x00
        response_frame = bytearray()
        if function_number == 0x1E:   
            response_frame.extend(bytes([0x48, 0x42, 0x14, 0x8F, 0x5C, 0x28, 0x34, 0x43]))
            self.adjustment_state = "idle"
        elif function_number == 0x16: 
            self.execute_tare()
            response_frame.extend(bytes([0x00]))  
        elif function_number == 0x18: 
            self.execute_zero_scaling()
            response_frame.extend(bytes([0x00]))  
        else: response_frame.extend(bytes([0x00]))
        final_tx_packet = bytearray([len(response_frame) + 2, 0x41]) + response_frame
        final_tx_packet.append(sum(final_tx_packet) % 256)
        return bytes(final_tx_packet)

    def _process_legacy_rs232_ascii(self, cmd: str) -> str:
        if cmd in {"ESC T", "TARE"}: self.execute_tare(); return "TARE ACK"
        if cmd in {"ESC V", "ZERO"}: self.execute_zero_scaling(); return "ZERO ACK"
        return f"WT + {self.last_display_value:,.4f} g"

    def _simulation_engine_tick(self):
        """Asynchronous cycle formatting metric variables based on accuracy parameter choices."""
        if self.machine_running:
            if not self.is_file_stream_active:
                self.simulated_load += (self.target_load - self.simulated_load) * 0.12
            
            raw_signal = self._generate_live_signal()
            transformed_net_weight = self._process_calibrated_weight(raw_signal)
            self.last_display_value = transformed_net_weight
            
            self._evaluate_measurement_stability(transformed_net_weight)
            stability_flag = " " if self.is_currently_stable else " [UNSTABLE]"
            
            # --- CAS BEHAVIORAL MAP: 1.1.8 Display Digit Resolution Truncations ---
            unit_label = " kg" if self.active_weight_unit == "1.1.7.3" else " g"
            if self.active_accuracy_digits == "1.1.8.7":     # Last digit off
                display_string_output = f"{transformed_net_weight:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.3":   # Index +1
                display_string_output = f"{transformed_net_weight:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.4":   # Index +2
                display_string_output = f"{transformed_net_weight:,.2f}"
            elif self.active_accuracy_digits == "1.1.8.5":   # Index +3
                display_string_output = f"{transformed_net_weight:,.1f}"
            elif self.active_accuracy_digits == "1.1.8.14":  # 10x resolution magnification
                display_string_output = f"{transformed_net_weight:,.5f}"
            else:                                            # All digits on (O)
                display_string_output = f"{transformed_net_weight:,.4f}"
                
            self.display_text.set(f"{display_string_output}{unit_label}{stability_flag}")
            self.raw_text.set(f"Raw Signal : {raw_signal:,.4f} g")
            
            if self.adjustment_state == "external adjustment":
                self.status_text.set("CAL.EXT" if not self.blink_on else "CALRUN")
            elif self.adjustment_state == "internal calibration":
                self.status_text.set("CAL.INT" if not self.blink_on else "CALRUN")
            else:
                self.status_text.set("ONLINE | METROLOGY RUNNING" if not self.blink_on else "ONLINE | DATA BUS ACTIVE")
        else:
            self.display_text.set("OFFLINE")
            self.raw_text.set(f"Raw Signal : {self.simulated_load:,.4f} g")

        # Dynamically loop updates matched to standard ticks
        self._scheduled_engine_loop_id = self.after(self.simulation_tick_rate_ms, self._simulation_engine_tick)

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
        try: self.after_cancel(self._scheduled_engine_loop_id)
        except: pass
        self.destroy()


if __name__ == "__main__":
    app = ModernWeighCellSimulator()
    app.mainloop()