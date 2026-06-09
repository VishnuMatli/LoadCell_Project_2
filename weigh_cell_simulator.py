import random
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


class ModernWeighCellSimulator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sartorius CAS Suite - Weigh Cell Emulation Environment")
        self.geometry("1500x900")
        self.minsize(1280, 820)
        
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
        
        # --- COMPLETE CAS CONFIGURATION PARAMETER TRACKING REGISTERS ---
        # 1.1 Setup Parameters
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

        # 3.1 - 3.4 Active Print Menu Parameters (25.pdf)
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

        # 2.1 - 2.9 Active Device Menu Parameters (26-28.pdf)
        self.dev_i1_protocol = "2.1.1.1"          
        self.dev_i1_baud = "2.1.2.7"              
        self.dev_i1_parity = "2.1.3.3"            
        self.dev_i1_stop_bits = "2.1.4.1"         
        self.dev_i1_handshake = "2.1.5.2"         
        self.dev_i1_data_bits = "2.1.6.1"         

        self.dev_i2_protocol = "2.2.1.1"          
        self.dev_i2_baud = "2.2.2.7"              
        self.dev_i2_parity = "2.2.3.3"            
        self.dev_i2_stop_bits = "2.2.4.1"         
        self.dev_i2_handshake = "2.2.5.2"         
        self.dev_i2_data_bits = "2.2.6.1"         
        self.dev_i2_detected = "2.2.7.0"        

        self.dev_add_menu = "2.9.1.2"              
        self.dev_add_keypad = "2.9.3.1"            
        self.dev_add_startup = "2.9.6.4"           
        self.dev_add_backlight = "2.9.8.2"         

        # 4.1 - 4.9 Active Application Menu Parameters
        self.active_app_mode = "4.1"
        self.app_unit_toggle = "g"
        self.app_counting_res = "Normal"
        self.app_counting_ref_update = "Automatic"
        self.app_percent_decimals = "2"
        self.app_net_total_print = "Component values"
        self.app_totalizing_print = "Summary string"
        self.app_animal_activity = "Stable"
        self.app_calc_method = "Multiplication"
        self.app_calc_decimals = "3"
        self.app_density_decimals = "4"

        # Complete Weight Unit Multiplier Map (1.1.7.2 to 1.1.7.23)
        self.unit_map = {
            "1.1.7.2":  {"name": "g",      "factor": 1.0},
            "1.1.7.3":  {"name": "kg",     "factor": 0.001},
            "1.1.7.4":  {"name": "mg",     "factor": 1000.0},
            "1.1.7.5":  {"name": "ct",     "factor": 5.0},
            "1.1.7.6":  {"name": "lb",     "factor": 0.00220462},
            "1.1.7.7":  {"name": "oz",     "factor": 0.035274},
            "1.1.7.8":  {"name": "ozt",    "factor": 0.0321507},
            "1.1.7.9":  {"name": "tlh",    "factor": 0.026717},
            "1.1.7.10": {"name": "tls",    "factor": 0.026455},
            "1.1.7.11": {"name": "tlt",    "factor": 0.026667},
            "1.1.7.12": {"name": "tlw",    "factor": 0.026460},
            "1.1.7.13": {"name": "gr",     "factor": 15.4324},
            "1.1.7.14": {"name": "dwt",    "factor": 0.643014},
            "1.1.7.15": {"name": "msg",    "factor": 0.26667},
            "1.1.7.16": {"name": "bkt",    "factor": 0.085735},
            "1.1.7.17": {"name": "parts",  "factor": 1.0},
            "1.1.7.18": {"name": "N",      "factor": 0.00980665},
            "1.1.7.19": {"name": "mo",     "factor": 0.26667},
            "1.1.7.20": {"name": "m",      "factor": 1.0},
            "1.1.7.21": {"name": "tls_t",  "factor": 0.026458},
            "1.1.7.22": {"name": "ae_gr",  "factor": 1.0},
            "1.1.7.23": {"name": "user",   "factor": 1.0}
        }

        # History and Communication Buffers
        self.filter_history_buffer = []
        self.is_currently_stable = True
        self.previous_weights_history = [0.0] * 5
        self.simulation_tick_rate_ms = 50         
        
        self.file_stream_buffer = []
        self.file_stream_index = 0
        self.is_file_stream_active = False
        self.loaded_file_path = ""
        self.adc_reference_scale = 535.0 / 44347000.0  
        self.command_history = []

        # Variable Allocation
        self.load_var = tk.DoubleVar(value=self.target_load)
        self.status_text = tk.StringVar(value="EMULATOR BUS CORE: STANDBY")
        self.display_text = tk.StringVar(value="------")
        self.raw_text = tk.StringVar(value="Transducer Input: 0.0000 g")
        self.scale_text = tk.StringVar(value="Calibration Scale: 1.000000")
        self.zero_text = tk.StringVar(value="Zero Offset: 0.0000 g")
        self.tare_text = tk.StringVar(value="Tare Offset: 0.0000 g")
        self.command_status_text = tk.StringVar(value="REMOTE BUS CONTROL: STANDBY")
        self.stream_status_text = tk.StringVar(value="INPUT TRACK: BALANCED SLIDER")

        # Setup Visual Theme Style Elements
        self._apply_theme_styles()
        self._build_hardware_layout()
        
        self.protocol("WM_DELETE_WINDOW", self._on_safe_close)

        # High-Fidelity Execution Loops
        self._scheduled_engine_loop_id = self.after(self.simulation_tick_rate_ms, self._simulation_engine_tick)
        self.after(350, self._status_blinker_tick)

    def _apply_theme_styles(self):
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
        
        style.configure("MainTitle.TLabel", background=bg_main, foreground=text_primary, font=("Segoe UI", 14, "bold"))
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

        # Specialized Android-Style UI Navigation components styles
        style.configure("AndroidHeader.TLabel", background="#1E293B", foreground="#38BDF8", font=("Segoe UI", 12, "bold"))
        style.configure("AndroidBtn.TButton", font=("Segoe UI", 10, "bold"), padding=10, background="#334155", foreground="#F8FAFC", anchor="w")
        style.map("AndroidBtn.TButton", background=[("active", "#475569")])
        style.configure("AndroidBack.TButton", font=("Segoe UI", 9, "bold"), padding=6, background="#475569", foreground="#38BDF8")

        style.configure("TRadiobutton", background="#1E293B", foreground="#F8FAFC", font=("Segoe UI", 10))
        style.map("TRadiobutton", background=[("active", "#1E293B")], foreground=[("active", "#38BDF8")])

    def _write_terminal_log(self, text):
        self.message.configure(state="normal")
        self.message.insert("end", text + "\n")
        self.message.see("end")
        self.message.configure(state="disabled")

    def _set_command_status(self, text):
        self.command_status_text.set(f"BUS STATUS: {text.upper()}")

    def _build_hardware_layout(self):
        master_content_container = ttk.Frame(self, style="TFrame")
        master_content_container.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ttk.Frame(master_content_container, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=0)

        title_subcontainer = ttk.Frame(header_frame, style="TFrame")
        title_subcontainer.grid(row=0, column=0, sticky="nw")
        
        ttk.Label(title_subcontainer, text="SARTORIUS CAS CONFIGURATION APP SIMULATOR", style="MainTitle.TLabel").pack(anchor="w")
        ttk.Label(title_subcontainer, text="High-precision system workspace mapped using an Android Settings App architecture pattern.", style="SubTitle.TLabel").pack(anchor="w", pady=(2, 0))

        btn_exit = ttk.Button(header_frame, text="EXIT SYSTEM", style="Exit.TButton", command=self._on_safe_close)
        btn_exit.grid(row=0, column=1, sticky="ne", padx=(10, 0), pady=2)

        workspace = ttk.Frame(master_content_container, style="TFrame")
        workspace.pack(fill="both", expand=True)
        
        workspace.columnconfigure(0, weight=6)  
        workspace.columnconfigure(1, weight=4)  
        workspace.columnconfigure(2, weight=4)  
        workspace.rowconfigure(0, weight=1)     

        # Android App Surface Container Panel
        self.sidebar_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        self.sidebar_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=5)
        
        # Initialize Android Base Root Page View
        self._render_android_root_view()

        left_panel = ttk.Frame(workspace, style="Card.TFrame", padding=0)
        left_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self._render_scrolling_control_ui(left_panel)

        right_panel = ttk.Frame(workspace, style="Card.TFrame", padding=15)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0), pady=5)
        self._render_telemetry_ui(right_panel)

    # --- ANDROID SETTINGS STYLE SURFACE ENGINE ---
    def _clear_android_surface(self):
        for child in self.sidebar_panel.winfo_children():
            child.destroy()

    def _render_android_root_view(self):
        self._clear_android_surface()

        ttk.Label(self.sidebar_panel, text="ACTIVE CAS SYSTEM SETTINGS", style="AndroidHeader.TLabel").pack(anchor="w", pady=(0, 15))

        menus = [
            ("Active Setup Menu          >", self._render_balance_menu),
            ("Active Device Menu         >", self._render_device_interfaces_menu),
            ("Active Print Menu          >", self._render_print_settings_menu),
            ("Active Appl. Menu          >", self._render_application_modes_menu),
            ("Factory Defaults Options   >", self._render_factory_reset_view)
        ]

        for text, callback in menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=4)

    def _add_android_back_row(self, title, back_callback):
        nav_row = ttk.Frame(self.sidebar_panel, style="TFrame")
        nav_row.pack(fill="x", pady=(0, 15))
        
        back_btn = ttk.Button(nav_row, text="< BACK", style="AndroidBack.TButton", command=back_callback)
        back_btn.pack(side="left", padx=(0, 10))

        ttk.Label(nav_row, text=title, style="AndroidHeader.TLabel").pack(side="left", fill="x")
        ttk.Separator(self.sidebar_panel, orient="horizontal").pack(fill="x", pady=(0, 10))

    # --- SUB-MENUS RESTORING COMPREHENSIVE SUBOPTIONS ---
    def _render_balance_menu(self):
        self._clear_android_surface()
        self._add_android_back_row("Active Setup Menu", self._render_android_root_view)

        sub_menus = [
            ("1.1.1 Installation Site / Ambient Conditions", lambda: self._render_radio_selector_page("Ambient Conditions", "1.1.1", [
                ("1.1.1.1 Very stable conditions", "1.1.1.1"),
                ("1.1.1.2 Stable conditions [Factory Default]", "1.1.1.2"),
                ("1.1.1.3 Unstable conditions", "1.1.1.3"),
                ("1.1.1.4 Very unstable conditions", "1.1.1.4")
            ], "active_env_filter", self._render_balance_menu)),
            
            ("1.1.2 Application Filter Processing", lambda: self._render_radio_selector_page("Application Filter", "1.1.2", [
                ("1.1.2.1 Final readout trace filter [Factory]", "1.1.2.1"),
                ("1.1.2.2 Dosing configuration mode", "1.1.2.2"),
                ("1.1.2.3 Reduced filter matrix path", "1.1.2.3"),
                ("1.1.2.4 Filter pipeline switched off", "1.1.2.4")
            ], "active_app_filter", self._render_balance_menu, clear_dsp=True)),

            ("1.1.3 Measurement Stability Range Bounds", lambda: self._render_radio_selector_page("Stability Range", "1.1.3", [
                ("1.1.3.1 1/4 Scale delta confirmation step", "1.1.3.1"),
                ("1.1.3.2 1/2 Scale delta confirmation step", "1.1.3.2"),
                ("1.1.3.3 1 Scale delta confirmation interval", "1.1.3.3"),
                ("1.1.3.4 2 Scale confirmation step [Factory]", "1.1.3.4"),
                ("1.1.3.5 4 Scale confirmation tracking step", "1.1.3.5"),
                ("1.1.3.6 8 Scale confirmation parsing step", "1.1.3.6")
            ], "active_stability_range", self._render_balance_menu)),

            ("1.1.4 Measurement Stability Delay", lambda: self._render_radio_selector_page("Stability Delay", "1.1.4", [
                ("1.1.4.1 Very Short latency parsing step", "1.1.4.1"),
                ("1.1.4.2 Short latency latching window [O]", "1.1.4.2"),
                ("1.1.4.3 Moderate tracking delay cycle", "1.1.4.3"),
                ("1.1.4.4 Long tracking delay timeline window", "1.1.4.4")
            ], "active_stability_delay", self._render_balance_menu)),

            ("1.1.5 Taring Structural Operations Mode", lambda: self._render_radio_selector_page("Taring Mode", "1.1.5", [
                ("1.1.5.1 Execute without verification stability", "1.1.5.1"),
                ("1.1.5.2 Execute after stability locked [O]", "1.1.5.2")
            ], "active_taring_mode", self._render_balance_menu)),

            ("1.1.6 Auto-Zero Origin Drift Tracking", lambda: self._render_radio_selector_page("Autozero Status", "1.1.6", [
                ("1.1.6.1 Automatic origin adjustments ON [O]", "1.1.6.1"),
                ("1.1.6.2 Automatic origin tracking OFF", "1.1.6.2")
            ], "active_autozero", self._render_balance_menu)),

            ("1.1.7 Instrumentation Multi-Unit Mapping", lambda: self._render_radio_selector_page("Weight Conversion Unit", "1.1.7", [
                (f"{k} Active mapping logic: {v['name']}" + (" [Factory]" if k == "1.1.7.2" else ""), k) for k, v in self.unit_map.items()
            ], "active_weight_unit", self._render_balance_menu)),

            ("1.1.8 Display Rounding Index Precision", lambda: self._render_radio_selector_page("Display Accuracy", "1.1.8", [
                ("1.1.8.1 All standard data digits on [O]", "1.1.8.1"),
                ("1.1.8.2 Toggle last rounding digit active", "1.1.8.2"),
                ("1.1.8.3 Scale accuracy step magnified +1", "1.1.8.3"),
                ("1.1.8.4 Scale accuracy step magnified +2", "1.1.8.4"),
                ("1.1.8.5 Scale accuracy step magnified +3", "1.1.8.5"),
                ("1.1.8.6 Force last digit scale interval 1", "1.1.8.6"),
                ("1.1.8.7 Truncate last output string digit", "1.1.8.7"),
                ("1.1.8.14 Magnify layout reading by 10x", "1.1.8.14")
            ], "active_accuracy_digits", self._render_balance_menu)),

            ("1.1.9 Calibration & Adjustment Functions", lambda: self._render_radio_selector_page("Calibration Function", "1.1.9", [
                ("1.1.9.1 Ext Adjustment Default Weight [Factory]", "1.1.9.1"),
                ("1.1.9.3 Ext Adjustment User Defined Weight", "1.1.9.3"),
                ("1.1.9.4 Internal Adjustment Profile Loop", "1.1.9.4"),
                ("1.1.9.6 Ext Linearization Default Weight Setup", "1.1.9.6"),
                ("1.1.9.7 Ext Linearization User Assigned Weight", "1.1.9.7"),
                ("1.1.9.8 Set Preload Value Register Mappings", "1.1.9.8"),
                ("1.1.9.9 Delete Preload Value Register Buffer", "1.1.9.9"),
                ("1.1.9.10 Calibration Key/Command Blocked Security", "1.1.9.10"),
                ("2.1.9.12 Selection List Path Parameters", "2.1.9.12"),
                ("3.1.9.18 Define Internal Weight Register Values", "3.1.9.18")
            ], "active_cal_func", self._render_balance_menu)),

            ("1.1.10 Pre-Calibration Process Pipeline", lambda: self._render_radio_selector_page("Adjustment Process", "1.1.10", [
                ("1.1.10.1 Adjust immediately structural sequence", "1.1.10.1"),
                ("1.1.10.2 Calibration before adjustment routines", "1.1.10.2")
            ], "active_adjust_process", self._render_balance_menu)),

            ("1.1.11 Manual Zero Point Boundary Ranges", lambda: self._render_radio_selector_page("Zero Range Limits", "1.1.11", [
                ("1.1.11.2 2% of Max Load tracking threshold", "1.1.11.2"),
                ("1.1.11.4 10% of Max Load tracking threshold", "1.1.11.4")
            ], "active_zero_range", self._render_balance_menu)),

            ("1.1.12 Origin Target Load Zero at Power On", lambda: self._render_radio_selector_page("Power On Zero Range", "1.1.12", [
                ("1.1.12.4 10% Max Load tolerance [Factory]", "1.1.12.4"),
                ("1.1.12.7 100% Max Load wide calibration tracking", "1.1.12.7")
            ], "active_poweron_zero", self._render_balance_menu)),

            ("1.1.13 Clear Buffer Registers at Power On", lambda: self._render_radio_selector_page("Tare/Zero At Power On", "1.1.13", [
                ("1.1.13.1 Active data pipeline cleaning ON", "1.1.13.1"),
                ("1.1.13.2 Active data pipeline cleaning OFF", "1.1.13.2")
            ], "active_poweron_tarezero", self._render_balance_menu)),

            ("1.1.14 Transducer Data Update Clock Rate", lambda: self._render_radio_selector_page("Data Clock Output Rate", "1.1.14", [
                ("1.1.14.1 Standard tracking updating rate", "1.1.14.1"),
                ("1.1.14.2 High performance processing rate", "1.1.14.2"),
                ("1.1.14.3 Slow automation sample clock 10Hz", "1.1.14.3"),
                ("1.1.14.4 Moderate automation clock 20Hz", "1.1.14.4"),
                ("1.1.14.5 Quick automation sample loop 25Hz", "1.1.14.5"),
                ("1.1.14.6 Fast processing sample loop 50Hz", "1.1.14.6"),
                ("1.1.14.7 Performance execution loop 100Hz", "1.1.14.7")
            ], "active_output_rate", self._render_balance_menu, clear_dsp=True)),

            ("1.1.15 IsoCal Automatic Internal Reminders", lambda: self._render_radio_selector_page("ISOCAL System Notes", "1.1.15", [
                ("1.1.15.1 Disable automatic isocal warnings", "1.1.15.1"),
                ("1.1.15.2 Enable automatic isocal message notes", "1.1.15.2")
            ], "active_isocal", self._render_balance_menu))
        ]

        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=3)

    def _render_device_interfaces_menu(self):
        self._clear_android_surface()
        self._add_android_back_row("Active Device Menu", self._render_android_root_view)

        sub_menus = [
            ("2.1 Interface 1 (RS232 Serial Port Control)   >", self._render_rs232_submenu),
            ("2.2 Interface 2 (USB Virtual COM Control)    >", self._render_usb_submenu),
            ("2.9 Additional System Core Function Setup     >", self._render_additional_submenu)
        ]

        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=4)

    def _render_rs232_submenu(self):
        self._clear_android_surface()
        self._add_android_back_row("RS232 Parameters", self._render_device_interfaces_menu)

        sub_menus = [
            ("2.1.1 Data Exchange Stream Protocol", lambda: self._render_radio_selector_page("RS232 Protocol", "2.1.1", [
                ("2.1.1.1 Standard ASCII SBI Mode [Factory]", "2.1.1.1"),
                ("2.1.1.2 Sartorius High Performance xBPI Core", "2.1.1.2"),
                ("2.1.1.4 Auxiliary SBI 2nd layout display panel", "2.1.1.4"),
                ("2.1.1.7 Universal formatting matrix printer (YDP20)", "2.1.1.7"),
                ("2.1.1.8 Lab reporting automation printer module (YDP30)", "2.1.1.8")
            ], "dev_i1_protocol", self._render_rs232_submenu)),
            
            ("2.1.2 Interface Clock Baud Speed", lambda: self._render_radio_selector_page("RS232 Baud Speed", "2.1.2", [
                (f"2.1.2.{i} Configuration value: {b} bps", f"2.1.2.{i}") for i, b in [("3","600"),("4","1200"),("5","2400"),("6","4800"),("7","9600 [O]"),("8","19200"),("9","38400"),("10","576000"),("11","115200")]
            ], "dev_i1_baud", self._render_rs232_submenu)),

            ("2.1.3 Structural Hardware Parity Checking", lambda: self._render_radio_selector_page("RS232 Parity Mask", "2.1.3", [
                ("2.1.3.3 Odd operational alignment [Factory]", "2.1.3.3"),
                ("2.1.3.4 Even operational alignment frame block", "2.1.3.4"),
                ("2.1.3.5 No parity tracking data bits allocated", "2.1.3.5")
            ], "dev_i1_parity", self._render_rs232_submenu)),

            ("2.1.4 Hardware End Stop Characters", lambda: self._render_radio_selector_page("RS232 Stop Bits", "2.1.4", [
                ("2.1.4.1 Mapped individual 1 stop bit character", "2.1.4.1"),
                ("2.1.4.2 Mapped secondary 2 stop bits character", "2.1.4.2")
            ], "dev_i1_stop_bits", self._render_rs232_submenu)),

            ("2.1.5 Interfaced Synchronization Flow Handshake", lambda: self._render_radio_selector_page("RS232 Flow Control", "2.1.5", [
                ("2.1.5.1 XON/XOFF text software handshake loop", "2.1.5.1"),
                ("2.1.5.2 CTS/RTS hardware serial handshake lines", "2.1.5.2"),
                ("2.1.5.3 No active workflow synchronization handshake", "2.1.5.3")
            ], "dev_i1_handshake", self._render_rs232_submenu)),

            ("2.1.6 Word Character Byte Word Size", lambda: self._render_radio_selector_page("RS232 Data Bits", "2.1.6", [
                ("2.1.6.1 7 block bit size characters configuration", "2.1.6.1"),
                ("2.1.6.2 8 block bit size characters configuration", "2.1.6.2")
            ], "dev_i1_data_bits", self._render_rs232_submenu))
        ]
        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=3)

    def _render_usb_submenu(self):
        self._clear_android_surface()
        self._add_android_back_row("USB Parameters", self._render_device_interfaces_menu)

        sub_menus = [
            ("2.2.1 Virtual Protocol Mode Layer", lambda: self._render_radio_selector_page("USB Protocol", "2.2.1", [
                ("2.2.1.1 Standard text stream ASCII SBI Mode", "2.2.1.1"),
                ("2.2.1.2 Native high speed binary xBPI Matrix", "2.2.1.2"),
                ("2.2.1.4 Secondary display auxiliary sync port", "2.2.1.4"),
                ("2.2.1.6 Spreadsheet direct matrix parsed output", "2.2.1.6"),
                ("2.2.1.7 Universal printing module tracking (YDP20)", "2.2.1.7"),
                ("2.2.1.8 Lab printer layout reporting sync (YDP30)", "2.2.1.8"),
                ("2.2.1.9 Text editor raw block direct injection", "2.2.1.9"),
                ("2.2.1.10 Off entire communication layer channel", "2.2.1.10")
            ], "dev_i2_protocol", self._render_usb_submenu)),

            ("2.2.2 Port Virtual Baud Sync speed", lambda: self._render_radio_selector_page("USB Baud Speed", "2.2.2", [
                (f"2.2.2.{i} Configuration value: {b} bps", f"2.2.2.{i}") for i, b in [("3","600"),("4","1200"),("5","2400"),("6","4800"),("7","9600"),("8","19200"),("9","38400"),("10","576000"),("11","115200")]
            ], "dev_i2_baud", self._render_usb_submenu)),

            ("2.2.3 Virtual Frame Verification Parity", lambda: self._render_radio_selector_page("USB Parity Mask", "2.2.3", [
                ("2.2.3.3 Odd framework check parity layer", "2.2.3.3"),
                ("2.2.3.4 Even framework validation check layer", "2.2.3.4"),
                ("2.2.3.5 No parity character validation bits", "2.2.3.5")
            ], "dev_i2_parity", self._render_usb_submenu)),

            ("2.2.4 Stop Framing Structures Alignment", lambda: self._render_radio_selector_page("USB Stop Bits", "2.2.4", [
                ("2.2.4.1 Individual 1 stop tracking bit frame", "2.2.4.1"),
                ("2.2.4.2 Secondary 2 stop tracking bits frame", "2.2.4.2")
            ], "dev_i2_stop_bits", self._render_usb_submenu)),

            ("2.2.5 Virtual Stream Intercept Handshake", lambda: self._render_radio_selector_page("USB Flow Control", "2.2.5", [
                ("2.2.5.2 Hardware protocol pipeline handshake", "2.2.5.2"),
                ("2.2.5.3 No handshake validation logic checked", "2.2.5.3")
            ], "dev_i2_handshake", self._render_usb_submenu)),

            ("2.2.6 Virtual Bus Data Byte Word Size", lambda: self._render_radio_selector_page("USB Data Bits", "2.2.6", [
                ("2.2.6.1 7 data bits layout structure definition", "2.2.6.1"),
                ("2.2.6.2 8 data bits layout structure definition", "2.2.6.2")
            ], "dev_i2_data_bits", self._render_usb_submenu)),

            ("2.2.7 Auto Sensing USB Attachment States", lambda: self._render_radio_selector_page("USB Peripheral Detection", "2.2.7", [
                ("2.2.7.0 Generic host/printer default tracking link", "2.2.7.0")
            ], "dev_i2_detected", self._render_usb_submenu))
        ]
        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=3)

    def _render_additional_submenu(self):
        self._clear_android_surface()
        self._add_android_back_row("Additional Functions", self._render_device_interfaces_menu)

        sub_menus = [
            ("2.9.1 Parameter Editing Menu Restrictions", lambda: self._render_radio_selector_page("Menu Access Edit", "2.9.1", [
                ("2.9.1.1 Full modifications allowed to configurations", "2.9.1.1"),
                ("2.9.1.2 Read-Only secure locking enabled [Factory]", "2.9.1.2")
            ], "dev_add_menu", self._render_additional_submenu)),

            ("2.9.3 Console Tactile Keypad Lockout", lambda: self._render_radio_selector_page("Keypad Locks", "2.9.3", [
                ("2.9.3.1 Front panel interface keys available", "2.9.3.1"),
                ("2.9.3.2 Front panel button switches BLOCKED", "2.9.3.2")
            ], "dev_add_keypad", self._render_additional_submenu)),

            ("2.9.6 Instrumentation Boot Initialization", lambda: self._render_radio_selector_page("Startup Routine Strategy", "2.9.6", [
                ("2.9.6.3 Enter standby state upon power connection", "2.9.6.3"),
                ("2.9.6.4 Execute automatic on power sequence [Factory]", "2.9.6.4")
            ], "dev_add_startup", self._render_additional_submenu)),
            
            ("2.9.8 Visual Display Backlight Profile", lambda: self._render_radio_selector_page("Display Backlight", "2.9.8", [
                ("2.9.8.1 Deactivate panel illumination [OFF]", "2.9.8.1"),
                ("2.9.8.2 Activate illumination matrix [ON]", "2.9.8.2")
            ], "dev_add_backlight", self._render_additional_submenu, update_backlight=True))
        ]
        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=3)

    def _render_print_settings_menu(self):
        self._clear_android_surface()
        self._add_android_back_row("Active Print Menu", self._render_android_root_view)

        sub_menus = [
            ("3.1.1 Automated Data Output Sync", lambda: self._render_radio_selector_page("Data Output Trigger", "3.1.1", [
                ("3.1.1.1 Individual reading without stability", "3.1.1.1"),
                ("3.1.1.2 Individual reading after stability latch", "3.1.1.2"),
                ("3.1.1.4 Continuous broadcast stream un-stabilized", "3.1.1.4"),
                ("3.1.1.5 Continuous broadcast stream after stability", "3.1.1.5")
            ], "print_data_output", self._render_print_settings_menu)),

            ("3.1.2 Automatic Transmission Intercept Rule", lambda: self._render_radio_selector_page("Cancel Auto Output", "3.1.2", [
                ("3.1.2.1 Active automated print cancellation disabled", "3.1.2.1"),
                ("3.1.2.2 Intercept and stop via print key commands", "3.1.2.2")
            ], "print_cancel_auto", self._render_print_settings_menu)),

            ("3.1.3 Suppress Repeated Transmissions Cycle", lambda: self._render_radio_selector_page("Skip Auto Print Cycles", "3.1.3", [
                ("3.1.3.1 Send every single raw telemetry line value", "3.1.3.1"),
                ("3.1.3.2 Filter and skip every alternate value line", "3.1.3.2")
            ], "print_cycle_auto", self._render_print_settings_menu)),

            ("3.1.4 Serial Stream Block Data Width size", lambda: self._render_radio_selector_page("Output Text Data Width", "3.1.4", [
                ("3.1.4.1 16 characters raw metrics short string block", "3.1.4.1"),
                ("3.1.4.2 22 characters explicit expanded index identification", "3.1.4.2")
            ], "print_output_format", self._render_print_settings_menu)),

            ("3.2.1 Manual Console Printing Synch Type", lambda: self._render_radio_selector_page("Print Key Behavior", "3.2.1", [
                ("3.2.1.1 Print instantly regardless of weight stability", "3.2.1.1"),
                ("3.2.1.2 Latch weight stability before print execution", "3.2.1.2"),
                ("3.2.1.6 Print automatically when load delta variance shifts", "3.2.1.6")
            ], "print_trigger_type", self._render_print_settings_menu)),

            ("3.2.2 Formatted Document Layout Rule Mapping", lambda: self._render_radio_selector_page("Print layout Identification", "3.2.2", [
                ("3.2.2.2 Mapped structured application document standard", "3.2.2.2")
            ], "print_layout_format", self._render_print_settings_menu)),

            ("3.2.3 Output Metadata Parameters Field Block", lambda: self._render_radio_selector_page("Visible Application Fields", "3.2.3", [
                ("3.2.3.1 Hide metadata parameter strings from sheets", "3.2.3.1"),
                ("3.2.3.2 Write complete explicit configuration values list", "3.2.3.2"),
                ("3.2.3.3 Restrict block to main critical identifiers", "3.2.3.3")
            ], "print_appl_param", self._render_print_settings_menu)),

            ("3.2.4 GLP/GMP Quality Audit Report Generation", lambda: self._render_radio_selector_page("GLP Compliance Logging", "3.2.4", [
                ("3.2.4.1 Turn off automated audit logs [Factory Default]", "3.2.4.1"),
                ("3.2.4.2 Print logs exclusively after calibration changes", "3.2.4.2"),
                ("3.2.4.3 Append standard validation logs to printouts", "3.2.4.3")
            ], "print_glp_protocol", self._render_print_settings_menu)),

            ("3.3.1 Data Bus Decimal Radix Mark", lambda: self._render_radio_selector_page("Decimal Separator", "3.3.1", [
                ("3.3.1.1 Standard point decimal notation [.]", "3.3.1.1"),
                ("3.3.1.2 Standard comma decimal notation [,]", "3.3.1.2")
            ], "pc_decimal_separator", self._render_print_settings_menu)),

            ("3.3.2 Ingested String Output Filter Profile", lambda: self._render_radio_selector_page("Bus Output Format", "3.3.2", [
                ("3.3.2.1 Output alpha metadata text and numerical value", "3.3.2.1"),
                ("3.3.2.2 Strip alpha records and send numerical only", "3.3.2.2")
            ], "pc_output_format", self._render_print_settings_menu))
        ]
        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=3)

    def _render_application_modes_menu(self):
        self._clear_android_surface()
        self._add_android_back_row("Application Modes", self._render_android_root_view)

        sub_menus = [
            ("4.1 Standard Metrological Weighing Only", lambda: self._render_radio_selector_page("Weighing Configuration", "4.1", [
                ("4.1.1 Baseline analytical weight tracing setup", "4.1")
            ], "active_app_mode", self._render_application_modes_menu)),

            ("4.3 Industrial Piece Counting Module", lambda: self._render_radio_selector_page("Counting Accuracy Resolution", "4.3.1", [
                ("4.3.1.1 Standard piece scanning resolution profile", "Normal"),
                ("4.3.1.2 High accuracy sample grid computation profile", "High")
            ], "app_counting_res", self._render_application_modes_menu, set_app_mode="4.3")),

            ("4.3.2 Adaptive Counting Reference Optimization", lambda: self._render_radio_selector_page("Counting Reference Updating", "4.3.2", [
                ("4.3.2.1 Automatic mathematical dynamic sample update", "Automatic"),
                ("4.3.2.2 Freeze and anchor static sample weight baseline", "Manual")
            ], "app_counting_ref_update", self._render_application_modes_menu)),

            ("4.4 Percentage Truncation Output Format", lambda: self._render_radio_selector_page("Percent Mode Rounding Accuracy", "4.4", [
                ("4.4.1 Round percent string to individual decimal location", "1"),
                ("4.4.2 Round percent string to secondary decimal location", "2")
            ], "app_percent_decimals", self._render_application_modes_menu, set_app_mode="4.4")),

            ("4.5 Multi-Recipe Net Total Formulation Layout", lambda: self._render_radio_selector_page("Net Total Sheet Printing", "4.5", [
                ("4.5.1 Write distinct ingredient weight itemized records", "Component values"),
                ("4.5.2 Restrict to total accumulation weight summary", "Total sum metrics")
            ], "app_net_total_print", self._render_application_modes_menu, set_app_mode="4.5")),

            ("4.6 Storage Totalizing Accumulator Layout", lambda: self._render_radio_selector_page("Totalizing Format Output", "4.6", [
                ("4.6.1 Print summary string total statistics blocks", "Summary string")
            ], "app_totalizing_print", self._render_application_modes_menu, set_app_mode="4.6")),

            ("4.7 Dynamic Sensor Animal Balance Averaging", lambda: self._render_radio_selector_page("Vibration Dampening Filters", "4.7.1", [
                ("4.7.1.1 Standard environmental site dampening filters", "Stable"),
                ("4.7.1.2 High oscillation hyperactive movement averaging", "Hyperactive")
            ], "app_animal_activity", self._render_application_modes_menu, set_app_mode="4.7")),

            ("4.8 Mathematical Equation Factor Scaling", lambda: self._render_radio_selector_page("Formula Engine Operators Mapped", "4.8.1", [
                ("4.8.1.1 Apply multiplication factor multiplier scaling", "Multiplication"),
                ("4.8.1.2 Apply division divisor value factor scaling", "Division")
            ], "app_calc_method", self._render_application_modes_menu, set_app_mode="4.8")),

            ("4.8.2 Mathematical Scaling Truncation Bounds", lambda: self._render_radio_selector_page("Formula Decimal Outputs Precision", "4.8.2", [
                ("4.8.2.1 Truncate result string to 3 placement positions", "3")
            ], "app_calc_decimals", self._render_application_modes_menu)),

            ("4.9 Metrological Liquid Density Determination", lambda: self._render_radio_selector_page("Density Rounding Specifications", "4.9", [
                ("4.9.1 Force 4 decimal precision placement formatting", "4")
            ], "app_density_decimals", self._render_application_modes_menu, set_app_mode="4.9"))
        ]
        for text, callback in sub_menus:
            btn = ttk.Button(self.sidebar_panel, text=text, style="AndroidBtn.TButton", command=callback)
            btn.pack(fill="x", pady=3)

    def _render_factory_reset_view(self):
        self._clear_android_surface()
        self._add_android_back_row("Factory Settings", self._render_android_root_view)

        ttk.Label(self.sidebar_panel, text="Wipe configuration database registers back to baseline industrial standards?", 
                  style="FieldLabel.TLabel", wraplength=400).pack(anchor="w", pady=10)

        reset_btn = ttk.Button(self.sidebar_panel, text="CONFIRM RESET MATRIX (1.9.1.1)", style="Stop.TButton", command=self._execute_factory_menu_reset)
        reset_btn.pack(fill="x", pady=15)

    # --- GENERIC LEAF RADIO OPTION PAGE BUILDER MATRIX ---
    def _render_radio_selector_page(self, title, group_code, options, target_attr, back_callback, 
                                     clear_dsp=False, update_backlight=False, set_app_mode=None):
        self._clear_android_surface()
        self._add_android_back_row(title, back_callback)

        current_val = getattr(self, target_attr)
        tk_var = tk.StringVar(value=current_val)

        def _on_radio_mutated():
            selected_code = tk_var.get()
            setattr(self, target_attr, selected_code)
            self._write_terminal_log(f"[ANDROID APP UI] State mutated -> Code assigned: {selected_code}")
            self._set_command_status(f"REGISTRY CODE OPERATIVE: {selected_code}")

            if clear_dsp:
                self.filter_history_buffer.clear()
                if selected_code.startswith("1.1.14") or selected_code.startswith("2.1.2") or selected_code.startswith("2.2.2"):
                    self._reconfigure_asynchronous_clock_intervals(selected_code)
            
            if update_backlight:
                if selected_code == "2.9.8.1":
                    self.display_label.config(fg="#155E27", bg="#020617")
                else:
                    self.display_label.config(fg="#22C55E", bg="#0F172A")

            if set_app_mode:
                self.active_app_mode = set_app_mode

        radio_card = ttk.Frame(self.sidebar_panel, style="Card.TFrame", padding=15)
        radio_card.pack(fill="both", expand=True)

        for label_text, data_code in options:
            rb = ttk.Radiobutton(radio_card, text=label_text, value=data_code, variable=tk_var, command=_on_radio_mutated)
            rb.pack(anchor="w", pady=6)

    def _on_slider_adjustment(self, val):
        try:
            self.target_load = float(val)
        except ValueError:
            self.target_load = 0.0
        self.load_lbl_hint.configure(text=f"Targeted Mass: {self.target_load:,.4f} g")

    # --- SCROLLABLE SIDEBAR TRANSDUCER MANIPULATION PANELS ---
    def _render_scrolling_control_ui(self, parent_frame):
        control_canvas = tk.Canvas(parent_frame, bg="#1E293B", bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=control_canvas.yview)
        
        scrollable_content = ttk.Frame(control_canvas, style="ScrollCard.TFrame", padding=15)
        scrollable_content.bind("<Configure>", lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all")))
        
        control_canvas.create_window((0, 0), window=scrollable_content, anchor="nw", width=360)
        control_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        control_canvas.pack(side="left", fill="both", expand=True)

        ttk.Label(scrollable_content, text="SYSTEM INITIALIZATION", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 5))
        power_row = ttk.Frame(scrollable_content, style="TFrame")
        power_row.pack(fill="x", pady=(0, 15))
        ttk.Button(power_row, text="START CELL", style="Start.TButton", command=self.start_machine).pack(side="left")
        ttk.Button(power_row, text="STOP INTEL", style="Stop.TButton", command=self.stop_machine).pack(side="left", padx=10)

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

        ttk.Label(cal_grid, text="Manual Scaling factor multiplier", style="FieldLabel.TLabel").pack(anchor="w", pady=(4, 2))
        self.manual_scale_str = tk.StringVar(value="1.000000")
        self.entry_scale = ttk.Entry(cal_grid, textvariable=self.manual_scale_str)
        self.entry_scale.pack(fill="x", pady=2)
        ttk.Button(cal_grid, text="Apply Scalar Factor", style="Action.TButton", command=self.apply_manual_scaling).pack(fill="x", pady=(0, 8))

        ttk.Label(cal_grid, text="Auto-Calibration Reference (g)", style="FieldLabel.TLabel").pack(anchor="w", pady=(2, 2))
        self.auto_ref_str = tk.StringVar(value="500.0")
        self.entry_ref = ttk.Entry(cal_grid, textvariable=self.auto_ref_str)
        self.entry_ref.pack(fill="x", pady=2)
        ttk.Button(cal_grid, text="Compute Auto Span", style="Action.TButton", command=self.execute_auto_scale).pack(fill="x", pady=(0, 12))

        ttk.Button(scrollable_content, text="Zero-Scale Position", style="Action.TButton", command=self.execute_zero_scaling).pack(fill="x", pady=2)
        ttk.Button(scrollable_content, text="Tare Container Offsets", style="Action.TButton", command=self.execute_tare).pack(fill="x", pady=2)
        ttk.Button(scrollable_content, text="Flush Subsystem Pipeline", style="Action.TButton", command=self.reset_entire_pipeline).pack(fill="x", pady=(2, 0))

    def _render_telemetry_ui(self, parent):
        ttk.Label(parent, text="METROLOGICAL TELEMETRY MONITOR HUD", style="CardTitle.TLabel").pack(anchor="w")

        display_housing = tk.Frame(parent, bg="#334155", padx=4, pady=4, relief="sunken", borderwidth=2)
        display_housing.pack(fill="x", pady=(10, 10))
        
        display_canvas = tk.Frame(display_housing, bg="#0F172A")
        display_canvas.pack(fill="x")
        tk.Label(display_canvas, text="SARTORIUS INDUSTRIAL WZB INDICATOR", bg="#0F172A", fg="#475569", font=("Segoe UI", 8, "bold")).pack(anchor="nw", padx=10, pady=(6, 0))
        
        self.display_label = tk.Label(
            display_canvas, textvariable=self.display_text, bg="#0F172A", fg="#22C55E",
            font=("Consolas", 24, "bold"), anchor="e", padx=10, pady=10
        )
        self.display_label.pack(fill="x")

        status_bar = ttk.Frame(parent, style="Card.TFrame")
        status_bar.pack(fill="x", pady=(0, 10))

        self.blinker_canvas = tk.Canvas(status_bar, width=22, height=22, bg="#1E293B", highlightthickness=0)
        self.blinker_canvas.pack(side="left", padx=(2, 0))
        self.blinker_node = self.blinker_canvas.create_oval(4, 4, 18, 18, fill="#64748B", outline="#334155")

        ttk.Label(status_bar, textvariable=self.status_text, style="Metric.TLabel").pack(side="left", padx=8)

        matrix_box = tk.Frame(parent, bg="#0F172A", highlightbackground="#334155", highlightthickness=1, padx=12, pady=10)
        matrix_box.pack(fill="x", pady=(0, 14))

        ttk.Label(matrix_box, textvariable=self.raw_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.scale_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.zero_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.tare_text, style="Metric.TLabel", background="#0F172A").pack(anchor="w", pady=2)
        ttk.Label(matrix_box, textvariable=self.command_status_text, style="Metric.TLabel", background="#0F172A", foreground="#4ADE80").pack(anchor="w", pady=2)

        terminal_container = tk.Frame(parent, bg="#0F172A", highlightbackground="#334155", highlightthickness=1)
        terminal_container.pack(fill="both", expand=True)
        
        term_scroll = tk.Scrollbar(terminal_container, orient="vertical")
        self.message = tk.Text(terminal_container, yscrollcommand=term_scroll.set, wrap="word", bg="#0F172A", fg="#94A3B8", relief="flat", font=("Consolas", 9))
        
        term_scroll.config(command=self.message.yview)
        term_scroll.pack(side="right", fill="y")
        self.message.pack(side="left", fill="both", expand=True)
        
        self.message.insert("end", "[CORE_BUS] Multi-protocol configuration registers initialized.\n")
        self.message.configure(state="disabled")

        command_box = ttk.Frame(parent, style="Card.TFrame")
        command_box.pack(fill="x", pady=(12, 0))
        
        self.lbl_mode_indicator = ttk.Label(command_box, text="Active Decoder: SBI / xBPI DUAL LINK", font=("Segoe UI", 9, "bold"), foreground="#38BDF8")
        self.lbl_mode_indicator.pack(anchor="w", pady=2)
        
        entry_row = ttk.Frame(command_box, style="TFrame")
        entry_row.pack(fill="x")
        self.command_var = tk.StringVar(value="04 01 09 1E 2C")  
        self.command_entry = ttk.Entry(entry_row, textvariable=self.command_var)
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(entry_row, text="Transmit", style="Action.TButton", command=self.send_command).pack(side="right")

    # --- TRANSMISSION RATINGS HANDLERS ENGINE ---
    def _reconfigure_asynchronous_clock_intervals(self, code):
        rate_mappings = {
            "1.1.14.1": 50, "1.1.14.2": 40, "1.1.14.3": 100, "1.1.14.4": 50, "1.1.14.5": 40, "1.1.14.6": 20, "1.1.14.7": 10,
            "2.1.2.3": 500, "2.1.2.4": 250, "2.1.2.5": 120, "2.1.2.6": 80, "2.1.2.7": 50, "2.1.2.8": 25, "2.1.2.9": 15, "2.1.2.10": 10, "2.1.2.11": 5,
            "2.2.2.3": 500, "2.2.2.4": 250, "2.2.2.5": 120, "2.2.2.6": 80, "2.2.2.7": 50, "2.2.2.8": 25, "2.2.2.9": 15, "2.2.2.10": 10, "2.2.2.11": 5
        }
        self.simulation_tick_rate_ms = rate_mappings.get(code, 50)
        self._write_terminal_log(f"[CLOCK] Master asynchronous update ticker synced to: {self.simulation_tick_rate_ms}ms")

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
        
        self.dev_i1_protocol = "2.1.1.1"          
        self.dev_i1_baud = "2.1.2.7"              
        self.dev_i1_parity = "2.1.3.3"
        self.dev_i1_stop_bits = "2.1.4.1"
        self.dev_i1_handshake = "2.1.5.2"
        self.dev_i1_data_bits = "2.1.6.1"
        self.dev_i2_protocol = "2.2.1.1"          
        self.dev_i2_baud = "2.2.2.7"
        self.dev_i2_parity = "2.2.3.3"
        self.dev_i2_stop_bits = "2.2.4.1"
        self.dev_i2_handshake = "2.2.5.2"
        self.dev_i2_data_bits = "2.2.6.1"
        self.dev_i2_detected = "2.2.7.0"
        self.dev_add_menu = "2.9.1.2"
        self.dev_add_keypad = "2.9.3.1"            
        self.dev_add_startup = "2.9.6.4"
        self.dev_add_backlight = "2.9.8.2"         
        self.active_app_mode = "4.1"

        self.reset_entire_pipeline()
        self.display_label.config(fg="#22C55E", bg="#0F172A")
        self._render_android_root_view()
        self._write_terminal_log("[RESET] Subsystem registry database explicitly restored to deep factory benchmarks.")
        messagebox.showinfo("Factory Reset", "All CAS Subsystem configurations reverted.")

    def reset_entire_pipeline(self):
        self.zero_reference = 0.0
        self.tare_offset = 0.0
        self.scale_factor = 1.0
        self.manual_scale_str.set("1.000000")
        self.scale_text.set("Calibration Scale: 1.000000")
        self.zero_text.set("Zero Offset: 0.0000 g")
        self.tare_text.set("Tare Offset: 0.0000 g")

    def _process_calibrated_weight(self, raw_weight):
        net = (raw_weight - self.zero_reference) * self.scale_factor
        return net - self.tare_offset

    def _evaluate_measurement_stability(self, current_weight):
        self.previous_weights_history.append(current_weight)
        if len(self.previous_weights_history) > 5:
            self.previous_weights_history.pop(0)
        
        stability_map = {
            "1.1.3.1": 0.005, "1.1.3.2": 0.01, "1.1.3.3": 0.02, 
            "1.1.3.4": 0.05, "1.1.3.5": 0.1, "1.1.3.6": 0.2
        }
        allowed_delta = stability_map.get(self.active_stability_range, 0.05)
        max_deviation = max(self.previous_weights_history) - min(self.previous_weights_history)
        self.is_currently_stable = max_deviation <= allowed_delta

    def apply_manual_scaling(self):
        if self.dev_add_keypad == "2.9.3.2":
            messagebox.showerror("Access Blocked", "Front tactile console operations are BLOCKED (2.9.3.2).")
            return
        try:
            factor = float(self.manual_scale_str.get().strip())
        except ValueError:
            messagebox.showerror("Validation Fault", "Invalid numerical scalar index.")
            return
        if factor <= 0: return
        self.scale_factor = factor
        self.scale_text.set(f"Calibration Scale: {self.scale_factor:.6f}")

    def execute_zero_scaling(self):
        if self.dev_add_keypad == "2.9.3.2": return
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        max_allowed_zero = 820.0 if self.active_zero_range == "1.1.11.4" else 164.0  
        if abs(current_raw) > max_allowed_zero:
            messagebox.showerror("Zero Error", "Transducer offset out of bounds mapping constraints.")
            return
        self.zero_reference = current_raw
        self.zero_text.set(f"Zero Offset: {self.zero_reference:,.4f} g")

    def execute_tare(self):
        if self.dev_add_keypad == "2.9.3.2": return
        if self.active_taring_mode == "1.1.5.2" and not self.is_currently_stable:
            self._write_terminal_log("[TARE BLOCKED] Data line stream unstable.")
            return
        current_raw = self._generate_live_signal() if self.machine_running else self.simulated_load
        self.tare_offset = (current_raw - self.zero_reference) * self.scale_factor
        self.tare_text.set(f"Tare Offset: {self.tare_offset:,.4f} g")

    def execute_auto_scale(self):
        if self.dev_add_keypad == "2.9.3.2": return
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
            self._write_terminal_log(f"[INGESTION] Buffered {len(self.file_stream_buffer)} records successfully.")
        except Exception as e: messagebox.showerror("I/O Error", str(e))

    def _toggle_stream_source_mode(self):
        if not self.file_stream_buffer: return
        self.is_file_stream_active = not self.is_file_stream_active
        self.stream_status_text.set(f"INPUT TRACK: {self.loaded_file_path}" if self.is_file_stream_active else "INPUT TRACK: BALANCED SLIDER")

    def start_machine(self):
        if self.machine_running: return
        self.machine_running = True
        self.status_text.set("EMULATOR BUS CORE: ONLINE")
        self._write_terminal_log("[SYSTEM] Data telemetry processor pipeline started.")

    def stop_machine(self):
        if not self.machine_running: return
        self.machine_running = False
        self.blink_on = False
        self.status_text.set("EMULATOR BUS CORE: OFFLINE")
        self.blinker_canvas.itemconfig(self.blinker_node, fill="#64748B", outline="#334155")
        self.display_text.set("------")
        self._write_terminal_log("[SYSTEM] Data telemetry processor pipeline halted.")

    def send_command(self):
        raw_input = self.command_var.get().strip()
        if not raw_input: return
        if raw_input.upper().startswith("ESC") or not all(c in "0123456789ABCDEFabcdef " for c in raw_input):
            self.protocol_mode = "RS232/SBI"
            self.lbl_mode_indicator.config(text="Active Decoder: LEGACY RS232-SBI TERMINAL CORE", foreground="#EF4444")
            tx_frame = self._process_legacy_rs232_ascii(raw_input.upper())
            self._write_terminal_log(f"[RS232 RX] '{raw_input}' | [TX] -> {tx_frame}")
        else:
            self.protocol_mode = "xBPI"
            self.lbl_mode_indicator.config(text="Active Decoder: SARTORIUS xBPI COMPILER LINK", foreground="#4ADE80")
            try:
                byte_array = bytes.fromhex(raw_input)
                tx_bytes = self._process_binary_xbpi_frame(byte_array)
                tx_hex_string = " ".join(f"{b:02X}" for b in tx_bytes)
                self._write_terminal_log(f"[xBPI RX] {raw_input} | [TX] -> {tx_hex_string}")
            except Exception as e:
                self._write_terminal_log(f"[xBPI ERROR] Dropped structural frame logic: {str(e)}")

    def _process_binary_xbpi_frame(self, data: bytes) -> bytes:
        if len(data) < 3: 
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
        else: 
            response_frame.extend(bytes([0x00]))
            
        final_tx_packet = bytearray([len(response_frame) + 2, 0x41]) + response_frame
        final_tx_packet.append(sum(final_tx_packet) % 256)
        return bytes(final_tx_packet)

    def _process_legacy_rs232_ascii(self, cmd: str) -> str:
        if cmd in {"ESC T", "TARE"}: self.execute_tare(); return "TARE ACK"
        if cmd in {"ESC V", "ZERO"}: self.execute_zero_scaling(); return "ZERO ACK"
        return f"WT + {self.last_display_value:,.4f} g"

    def _generate_live_signal(self):
        if self.is_file_stream_active and self.file_stream_buffer:
            raw_adc = self.file_stream_buffer[self.file_stream_index]
            self.file_stream_index = (self.file_stream_index + 1) % len(self.file_stream_buffer)
            source_weight = raw_adc * self.adc_reference_scale
        else:
            source_weight = self.simulated_load

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
        
        if self.active_app_mode == "4.7" and self.app_animal_activity == "Hyperactive":
            filter_window_size = 65
        elif self.active_app_filter == "1.1.2.1": filter_window_size = 20
        elif self.active_app_filter == "1.1.2.2": filter_window_size = 8
        elif self.active_app_filter == "1.1.2.3": filter_window_size = 4
        else: filter_window_size = 1
            
        self.filter_history_buffer.append(raw_signal_output)
        if len(self.filter_history_buffer) > filter_window_size:
            self.filter_history_buffer.pop(0)
            
        return sum(self.filter_history_buffer) / len(self.filter_history_buffer)

    def _simulation_engine_tick(self):
        if self.machine_running:
            if not self.is_file_stream_active:
                self.simulated_load += (self.target_load - self.simulated_load) * 0.12
            
            raw_signal = self._generate_live_signal()
            transformed_net_weight = self._process_calibrated_weight(raw_signal)
            self.last_display_value = transformed_net_weight
            self._evaluate_measurement_stability(transformed_net_weight)
            stability_flag = " " if self.is_currently_stable else " [UNSTABLE]"
            
            unit_meta = self.unit_map.get(self.active_weight_unit, {"name": "g", "factor": 1.0})
            display_weight = transformed_net_weight * unit_meta["factor"]
            unit_label = f" {unit_meta['name']}"
            
            if self.active_accuracy_digits == "1.1.8.7": fmt_pattern = "{:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.3": fmt_pattern = "{:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.4": fmt_pattern = "{:,.2f}"
            elif self.active_accuracy_digits == "1.1.8.5": fmt_pattern = "{:,.1f}"
            elif self.active_accuracy_digits == "1.1.8.14": fmt_pattern = "{:,.5f}"
            else: fmt_pattern = "{:,.4f}"
                
            display_string_output = fmt_pattern.format(display_weight)
            
            if self.pc_output_format == "3.3.2.2":
                final_display_frame = f"{display_string_output}{stability_flag}"
            else:
                final_display_frame = f"{display_string_output}{unit_label}{stability_flag}"

            if self.pc_decimal_separator == "3.3.1.2":
                final_display_frame = final_display_frame.replace(".", ",")

            self.display_text.set(final_display_frame)
            self.raw_text.set(f"Transducer Input: {raw_signal:,.4f} g")
            
            if random.random() < 0.02:
                self._write_terminal_log(f"[TX TELEMETRY] Active App Mode Layer Context: {self.active_app_mode}")
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