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
        
        # --- CAS CONFIGURATION PARAMETER TRACKING REGISTERS ---
        # 1.1 Balance Parameters Baseline Settings
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

        # 3.1 - 3.3 Active Print Menu Parameter Registers (25.pdf)
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

        # 2.1 - 2.9 Active Device Menu Parameter Registers (26-28.pdf)
        self.dev_i1_protocol = "2.1.1.1"          
        self.dev_i1_baud = "9600"              
        self.dev_i1_parity = "Odd"            
        self.dev_i1_stop_bits = "1"         
        self.dev_i1_handshake = "Hardware Handshake"         
        self.dev_i1_data_bits = "7"         

        self.dev_i2_protocol = "2.2.1.1"          
        self.dev_i2_baud = "9600"              
        self.dev_i2_parity = "Odd"            
        self.dev_i2_stop_bits = "1"         
        self.dev_i2_handshake = "Hardware Handshake"         
        self.dev_i2_data_bits = "7"         
        self.dev_i2_detected = "None/printer/virt com./PC host/input device"        

        self.dev_add_menu = "2.9.1.2"              
        self.dev_add_keypad = "2.9.3.1"            
        self.dev_add_startup = "2.9.6.4"           
        self.dev_add_backlight = "2.9.8.2"         

        # 4.1 - 4.9 Active Application Menu Parameter Registers
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

        # Complete Weight Unit Multiplier Map (From 1.1.7.2 to 1.1.7.23)
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

        # Setup Layout Configuration Theme
        self._apply_theme_styles()
        self._build_hardware_layout()
        
        # Bind explicit treeview selection hook configuration mapping parameters
        self.cas_tree.bind("<<TreeviewSelect>>", self._on_cas_menu_node_click)
        self.protocol("WM_DELETE_WINDOW", self._on_safe_close)

        # High-Fidelity Asynchronous Execution Loops
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

        style.configure("Treeview", background="#1E293B", fieldbackground="#1E293B", foreground=text_primary, borderwidth=0, font=("Segoe UI", 9), rowheight=24)
        style.configure("Treeview.Heading", background="#334155", foreground=text_primary, font=("Segoe UI", 9, "bold"), padding=5)
        style.map("Treeview", background=[("selected", "#334155")], foreground=[("selected", "#38BDF8")])

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
            param_group, target_code = node_values[0], str(node_values[1])
            
            # --- ROUTING FOR LEVEL 1.1 BALANCE SETTINGS ---
            if param_group == "1.1.1":
                self.active_env_filter = target_code
                self._write_terminal_log(f"[CAS BALANCE] Ambient filter updated -> {target_code}")
            elif param_group == "1.1.2":
                self.active_app_filter = target_code
                self.filter_history_buffer.clear()
                self._write_terminal_log(f"[CAS BALANCE] Application filter modified -> {target_code}")
            elif param_group == "1.1.3":
                self.active_stability_range = target_code
                self._write_terminal_log(f"[CAS BALANCE] Stability range width updated -> {target_code}")
            elif param_group == "1.1.4":
                self.active_stability_delay = target_code
                self._write_terminal_log(f"[CAS BALANCE] Stability latch delay adjusted -> {target_code}")
            elif param_group == "1.1.5":
                self.active_taring_mode = target_code
                self._write_terminal_log(f"[CAS BALANCE] Taring behavior tracking method assigned -> {target_code}")
            elif param_group == "1.1.6":
                self.active_autozero = target_code
                self._write_terminal_log(f"[CAS BALANCE] Drift correction auto-zero state toggled -> {target_code}")
            elif param_group == "1.1.7":
                self.active_weight_unit = target_code
                self._write_terminal_log(f"[CAS BALANCE] Core base conversion metric weight unit -> {target_code}")
            elif param_group == "1.1.8":
                self.active_accuracy_digits = target_code
                self._write_terminal_log(f"[CAS BALANCE] Display rounding index resolution pattern -> {target_code}")
            elif param_group == "1.1.9":
                self.active_cal_func = target_code
                self._write_terminal_log(f"[CAS BALANCE] Calibration path profile assigned -> {target_code}")
            elif param_group == "1.1.10":
                self.active_adjust_process = target_code
                self._write_terminal_log(f"[CAS BALANCE] Pre-adjustment routine workflow structure -> {target_code}")
            elif param_group == "1.1.11":
                self.active_zero_range = target_code
                self._write_terminal_log(f"[CAS BALANCE] Manual zero tracking alignment bounds -> {target_code}")
            elif param_group == "1.1.12":
                self.active_poweron_zero = target_code
                self._write_terminal_log(f"[CAS BALANCE] Power-on offset zero threshold assigned -> {target_code}")
            elif param_group == "1.1.13":
                self.active_poweron_tarezero = target_code
                self._write_terminal_log(f"[CAS BALANCE] Clear power-on tracking offset buffer assigned -> {target_code}")
            elif param_group == "1.1.14":
                self.active_output_rate = target_code
                self._reconfigure_asynchronous_clock_intervals(target_code)
            elif param_group == "1.1.15":
                self.active_isocal = target_code
                self._write_terminal_log(f"[CAS BALANCE] Internal IsoCal reminder state parameter modified -> {target_code}")

            # --- ACTIVE PRINT MENU (3.1 - 3.3) --- [cite: 3]
            elif param_group == "3.1.1":
                self.print_data_output = target_code
                self._write_terminal_log(f"[PRINT] Data output sync assigned -> {target_code}")
            elif param_group == "3.1.2":
                self.print_cancel_auto = target_code
                self._write_terminal_log(f"[PRINT] Cancel automatic transmission criterion -> {target_code}")
            elif param_group == "3.1.3":
                self.print_cycle_auto = target_code
                self._write_terminal_log(f"[PRINT] Automatic printing skip cycle factor assigned -> {target_code}")
            elif param_group == "3.1.4":
                self.print_output_format = target_code
                self._write_terminal_log(f"[PRINT] Data string frame layout character width -> {target_code}")
            elif param_group == "3.2.1":
                self.print_trigger_type = target_code
                self._write_terminal_log(f"[PRINT] Manual layout print key sync mode assigned -> {target_code}")
            elif param_group == "3.2.2":
                self.print_layout_format = target_code
                self._write_terminal_log(f"[PRINT] Format reporting identity mapped -> {target_code}")
            elif param_group == "3.2.3":
                self.print_appl_param = target_code
                self._write_terminal_log(f"[PRINT] App parameters field output status toggled -> {target_code}")
            elif param_group == "3.2.4":
                self.print_glp_protocol = target_code
                self._write_terminal_log(f"[PRINT] GLP compliance system validation report log -> {target_code}")
            elif param_group == "3.3.1":
                self.pc_decimal_separator = target_code
                self._write_terminal_log(f"[PC-DIRECT] Radix decimal point separator assigned -> {target_code}")
            elif param_group == "3.3.2":
                self.pc_output_format = target_code
                self._write_terminal_log(f"[PC-DIRECT] Character encoding data layout pattern -> {target_code}")

            # --- ACTIVE DEVICE MENU (2.1 - 2.9) --- [cite: 10, 14, 20]
            elif param_group == "2.1.1":
                self.dev_i1_protocol = "xBPI" if target_code == "2.1.1.2" else "SBI"
                self._write_terminal_log(f"[RS232] Protocol assigned -> {self.dev_i1_protocol}")
            elif param_group == "2.1.2":
                baud_map = {"3":"600", "4":"1200", "5":"2400", "6":"4800", "7":"9600", "8":"19200", "9":"38400", "10":"576000", "11":"115200"}
                self.dev_i1_baud = baud_map.get(target_code.split(".")[-1], "9600")
                self._write_terminal_log(f"[RS232] Clock baud speed assigned -> {self.dev_i1_baud} bps")
            elif param_group == "2.1.3":
                p_map = {"3":"Odd", "4":"Even", "5":"No parity"}
                self.dev_i1_parity = p_map.get(target_code.split(".")[-1], "Odd")
                self._write_terminal_log(f"[RS232] Parity checking bit architecture configured -> {self.dev_i1_parity}")
            elif param_group == "2.1.4":
                self.dev_i1_stop_bits = "1" if target_code.split(".")[-1] == "1" else "2"
                self._write_terminal_log(f"[RS232] Transmit frame stop blocks assigned -> {self.dev_i1_stop_bits}")
            elif param_group == "2.1.5":
                h_map = {"1":"Software Handshake", "2":"Hardware Handshake", "3":"No handshake"}
                self.dev_i1_handshake = h_map.get(target_code.split(".")[-1], "Hardware Handshake")
                self._write_terminal_log(f"[RS232] Workflow pipeline handshake protocol assigned -> {self.dev_i1_handshake}")
            elif param_group == "2.1.6":
                self.dev_i1_data_bits = "7" if target_code.split(".")[-1] == "1" else "8"
                self._write_terminal_log(f"[RS232] Word size content data bit length assigned -> {self.dev_i1_data_bits}")

            # Interface 2 (USB) [cite: 14]
            elif param_group == "2.2.1":
                self.dev_i2_protocol = "xBPI" if target_code == "2.2.1.2" else "SBI"
                self._write_terminal_log(f"[USB] Protocol state profile mapped -> {self.dev_i2_protocol}")
            elif param_group == "2.2.2":
                baud_map = {"3":"600", "4":"1200", "5":"2400", "6":"4800", "7":"9600", "8":"19200", "9":"38400", "10":"576000", "11":"115200"}
                self.dev_i2_baud = baud_map.get(target_code.split(".")[-1], "9600")
                self._write_terminal_log(f"[USB] Clock speed baud rate assigned -> {self.dev_i2_baud} bps")
            elif param_group == "2.2.3":
                p_map = {"3":"Odd", "4":"Even", "5":"No parity"}
                self.dev_i2_parity = p_map.get(target_code.split(".")[-1], "Odd")
                self._write_terminal_log(f"[USB] Frame check parity layout architecture toggled -> {self.dev_i2_parity}")
            elif param_group == "2.2.4":
                self.dev_i2_stop_bits = "1" if target_code.split(".")[-1] == "1" else "2"
                self._write_terminal_log(f"[USB] Structural frame synchronization stop blocks -> {self.dev_i2_stop_bits}")
            elif param_group == "2.2.5":
                self.dev_i2_handshake = "Hardware Handshake" if target_code.split(".")[-1] == "2" else "No handshake"
                self._write_terminal_log(f"[USB] Flow control handshake protocol changed -> {self.dev_i2_handshake}")
            elif param_group == "2.2.6":
                self.dev_i2_data_bits = "7" if target_code.split(".")[-1] == "1" else "8"
                self._write_terminal_log(f"[USB] Character frame data bit word index length -> {self.dev_i2_data_bits}")
            elif param_group == "2.2.7":
                self.dev_i2_detected = "None/printer/virt com./PC host/input device"
                self._write_terminal_log("[USB] Attached hardware polling status checked.")

            # Additional function configuration routing [cite: 20]
            elif param_group == "2.9.1":
                self.dev_add_menu = target_code
                self._write_terminal_log(f"[ADDITIONAL] Config access rule updated -> {target_code}")
            elif param_group == "2.9.3":
                self.dev_add_keypad = target_code
                self._write_terminal_log(f"[ADDITIONAL] Keypad lock strategy updated -> {target_code}")
            elif param_group == "2.9.6":
                self.dev_add_startup = target_code
                self._write_terminal_log(f"[ADDITIONAL] Boot initial strategy applied -> {target_code}")
            elif param_group == "2.9.8":
                self.dev_add_backlight = target_code
                if target_code == "2.9.8.1":
                    self.display_label.config(fg="#155E27", bg="#020617") 
                    self._write_terminal_log("[ADDITIONAL] Backlight state toggled -> OFF.")
                else:
                    self.display_label.config(fg="#22C55E", bg="#0F172A")
                    self._write_terminal_log("[ADDITIONAL] Backlight state toggled -> ON.")

            # --- ACTIVE APPLICATION MENU (4.1 - 4.9) ---
            elif param_group == "4.1":
                self.active_app_mode = "4.1"
                self.app_unit_toggle = target_code
                self._write_terminal_log(f"[APP MODE] Weighing Only -> Assigned Unit: {target_code}")
            elif param_group == "4.3.1":
                self.active_app_mode = "4.3"
                self.app_counting_res = target_code
                self._write_terminal_log(f"[APP MODE] Counting -> Piece weight calculation resolution: {target_code}")
            elif param_group == "4.3.2":
                self.app_counting_ref_update = target_code
                self._write_terminal_log(f"[APP MODE] Counting -> Reference updating strategy: {target_code}")
            elif param_group == "4.4":
                self.active_app_mode = "4.4"
                self.app_percent_decimals = target_code
                self._write_terminal_log(f"[APP MODE] Percentage -> Assigned decimal rounding places: {target_code}")
            elif param_group == "4.5":
                self.active_app_mode = "4.5"
                self.app_net_total_print = target_code
                self._write_terminal_log(f"[APP MODE] Net Total Formulation -> Printout strategy component: {target_code}")
            elif param_group == "4.6":
                self.active_app_mode = "4.6"
                self.app_totalizing_print = target_code
                self._write_terminal_log(f"[APP MODE] Totalizing Formulation -> Printout component structure: {target_code}")
            elif param_group == "4.7.1":
                self.active_app_mode = "4.7"
                self.app_animal_activity = target_code
                self._write_terminal_log(f"[APP MODE] Animal activity threshold parameter bound -> {target_code}")
            elif param_group == "4.7.2":
                self._write_terminal_log("[APP MODE] Animal Balance tracking integration algorithm triggered manually.")
            elif param_group == "4.8.1":
                self.active_app_mode = "4.8"
                self.app_calc_method = target_code
                self._write_terminal_log(f"[APP MODE] Mathematical calculation profile -> {target_code}")
            elif param_group == "4.8.2":
                self.app_calc_decimals = target_code
                self._write_terminal_log(f"[APP MODE] Mathematical expression decimal output -> {target_code}")
            elif param_group == "4.9":
                self.active_app_mode = "4.9"
                self.app_density_decimals = target_code
                self._write_terminal_log(f"[APP MODE] Density calculation decimal truncation accuracy -> {target_code}")

            # --- FACTORY RESET SUBSYSTEM TRIGGER ---
            elif param_group == "1.9.1" and target_code == "1.9.1.1":
                self._execute_factory_menu_reset()
                    
            self._set_command_status(f"REGISTRY CODE OPERATIVE: {target_code}")

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
        self._write_terminal_log(f"[HARDWARE] Direct load injection complete: {target_mass:,.4f} g.")

    def _reconfigure_asynchronous_clock_intervals(self, code):
        rate_mappings = {
            "1.1.14.1": 50, "1.1.14.2": 40, "1.1.14.3": 100, "1.1.14.4": 50, "1.1.14.5": 40, "1.1.14.6": 20, "1.1.14.7": 10
        }
        self.simulation_tick_rate_ms = rate_mappings.get(code, 50)
        self._write_terminal_log(f"[CLOCK] Master asynchronous pipeline update rate -> {self.simulation_tick_rate_ms}ms")

    def _execute_factory_menu_reset(self):
        self.active_env_filter = "1.1.1.2"
        self.active_app_filter = "1.1.2.1"
        self.active_stability_range = "1.1.3.4"
        self.active_stability_delay = "1.1.4.2"
        self.active_taring_mode = "1.1.5.2"
        self.active_autozero = "1.1.6.1"
        self.active_weight_unit = "1.1.7.2"
        self.active_accuracy_digits = "1.1.8.1"
        
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

        self.dev_i1_protocol = "SBI"          
        self.dev_i1_baud = "9600"              
        self.dev_i1_parity = "Odd"            
        self.dev_i1_stop_bits = "1"         
        self.dev_i1_handshake = "Hardware Handshake"         
        self.dev_i1_data_bits = "7"         

        self.dev_i2_protocol = "SBI"          
        self.dev_i2_baud = "9600"              
        self.dev_i2_parity = "Odd"            
        self.dev_i2_stop_bits = "1"         
        self.dev_i2_handshake = "Hardware Handshake"         
        self.dev_i2_data_bits = "7"         
        self.dev_i2_detected = "None/printer/virt com./PC host/input device"        

        self.dev_add_menu = "2.9.1.2"              
        self.dev_add_keypad = "2.9.3.1"            
        self.dev_add_startup = "2.9.6.4"           
        self.dev_add_backlight = "2.9.8.2"         

        self.active_app_mode = "4.1"

        self.reset_entire_pipeline()
        self.display_label.config(fg="#22C55E", bg="#0F172A")
        self._write_terminal_log("[RESET] Subsystem registry database flushed to factory defaults.")
        messagebox.showinfo("Factory Reset", "Sartorius system profiles initialized successfully.")

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
            self._write_terminal_log(f"[INGESTION] Buffered {len(self.file_stream_buffer)} transducer records.")
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
                self._write_terminal_log(f"[xBPI ERROR] Dropped structural frame: {str(e)}")

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

    def _build_hardware_layout(self):
        master_content_container = ttk.Frame(self, style="TFrame")
        master_content_container.pack(fill="both", expand=True, padx=20, pady=20)

        header_frame = ttk.Frame(master_content_container, style="TFrame")
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=0)

        title_subcontainer = ttk.Frame(header_frame, style="TFrame")
        title_subcontainer.grid(row=0, column=0, sticky="nw")
        
        ttk.Label(title_subcontainer, text="SARTORIUS CAS CONFIGURATION & WEIGH SIMULATION SUITE", style="MainTitle.TLabel").pack(anchor="w")
        ttk.Label(title_subcontainer, text="High-precision test workspace mapping comprehensive multi-app parameters & complete metrological unit arrays.", style="SubTitle.TLabel").pack(anchor="w", pady=(2, 0))

        btn_exit = ttk.Button(header_frame, text="EXIT SYSTEM", style="Exit.TButton", command=self._on_safe_close)
        btn_exit.grid(row=0, column=1, sticky="ne", padx=(10, 0), pady=2)

        workspace = ttk.Frame(master_content_container, style="TFrame")
        workspace.pack(fill="both", expand=True)
        
        workspace.columnconfigure(0, weight=6)  
        workspace.columnconfigure(1, weight=4)  
        workspace.columnconfigure(2, weight=4)  
        workspace.rowconfigure(0, weight=1)     

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
        
        self.cas_tree.heading("#0", text="Complete Menu Hierarchy Registers Mapped", anchor="w")
        self.cas_tree.column("#0", minwidth=420, width=480, stretch=True)

        # LEVEL 1 CATEGORIES
        l1_setup = self.cas_tree.insert("", "end", text="1. Active Setup Menu", open=True)
        l1_print = self.cas_tree.insert("", "end", text="2. Active Print Menu", open=True)
        l1_device = self.cas_tree.insert("", "end", text="3. Active Device Menu", open=True)
        l1_apps = self.cas_tree.insert("", "end", text="4. Active Application Menu", open=True)

        # 1.1 Balance Settings [cite: 10]
        l2_balance = self.cas_tree.insert(l1_setup, "end", text="1.1 Balance Settings", open=True)
        l2_general = self.cas_tree.insert(l1_setup, "end", text="1.9 General Settings", open=True)
        
        l3_ambient = self.cas_tree.insert(l2_balance, "end", text="1.1.1 Installation Site / Ambient Conditions")
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.1 Very stable conditions", values=("1.1.1", "1.1.1.1"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.2 Stable conditions [Factory O]", values=("1.1.1", "1.1.1.2"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.3 Unstable conditions", values=("1.1.1", "1.1.1.3"))
        self.cas_tree.insert(l3_ambient, "end", text="1.1.1.4 Very unstable conditions", values=("1.1.1", "1.1.1.4"))

        l3_filter = self.cas_tree.insert(l2_balance, "end", text="1.1.2 Application Filter")
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.1 Final readout [Factory O]", values=("1.1.2", "1.1.2.1"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.2 Dosing mode", values=("1.1.2", "1.1.2.2"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.3 Reduced filter matrix", values=("1.1.2", "1.1.2.3"))
        self.cas_tree.insert(l3_filter, "end", text="1.1.2.4 Filter pipeline off", values=("1.1.2", "1.1.2.4"))

        l3_stability = self.cas_tree.insert(l2_balance, "end", text="1.1.3 Stability Range")
        for idx, step in enumerate(["1/4 Scale Interval", "1/2 Scale Interval", "1 Scale Interval", "2 Scale Interval [Factory O]", "4 Scale Interval", "8 Scale Interval"], 1):
            self.cas_tree.insert(l3_stability, "end", text=f"1.1.3.{idx} {step}", values=("1.1.3", f"1.1.3.{idx}"))

        l3_delay = self.cas_tree.insert(l2_balance, "end", text="1.1.4 Stability Delay")
        for idx, step in enumerate(["Very Short", "Short [Factory O]", "Moderate", "Long"], 1):
            self.cas_tree.insert(l3_delay, "end", text=f"1.1.4.{idx} {step}", values=("1.1.4", f"1.1.4.{idx}"))

        l3_taring = self.cas_tree.insert(l2_balance, "end", text="1.1.5 Taring Mode")
        self.cas_tree.insert(l3_taring, "end", text="1.1.5.1 Without stability", values=("1.1.5", "1.1.5.1"))
        self.cas_tree.insert(l3_taring, "end", text="1.1.5.2 After stability [Factory O]", values=("1.1.5", "1.1.5.2"))

        l3_autoz = self.cas_tree.insert(l2_balance, "end", text="1.1.6 Autozero Tracking")
        self.cas_tree.insert(l3_autoz, "end", text="1.1.6.1 ON [Factory O]", values=("1.1.6", "1.1.6.1"))
        self.cas_tree.insert(l3_autoz, "end", text="1.1.6.2 OFF", values=("1.1.6", "1.1.6.2"))

        # 1.1.7 FULL RESTORATION AND RANGE MAPPING (1.1.7.3 to 1.1.7.23)
        l3_unit = self.cas_tree.insert(l2_balance, "end", text="1.1.7 Weight Unit Selection")
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.1 Available unit list profile", values=("1.1.7", "1.1.7.1"))
        self.cas_tree.insert(l3_unit, "end", text="1.1.7.2 g, Gram [Factory O]", values=("1.1.7", "1.1.7.2"))
        for code_suffix, details in self.unit_map.items():
            if code_suffix == "1.1.7.2": continue
            self.cas_tree.insert(l3_unit, "end", text=f"{code_suffix} Unit mapped: {details['name']}", values=("1.1.7", code_suffix))

        l3_accuracy = self.cas_tree.insert(l2_balance, "end", text="1.1.8 Accuracy Configuration")
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.1 All digits on [Factory O]", values=("1.1.8", "1.1.8.1"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.2 Last digit on/off during transformation", values=("1.1.8", "1.1.8.2"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.3 Scale interval index +1", values=("1.1.8", "1.1.8.3"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.4 Scale interval index +2", values=("1.1.8", "1.1.8.4"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.5 Scale interval index +3", values=("1.1.8", "1.1.8.5"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.6 Last digit scale interval 1", values=("1.1.8", "1.1.8.6"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.7 Last digit off", values=("1.1.8", "1.1.8.7"))
        self.cas_tree.insert(l3_accuracy, "end", text="1.1.8.14 10x high validation magnification", values=("1.1.8", "1.1.8.14"))

        l3_cal = self.cas_tree.insert(l2_balance, "end", text="1.1.9 Calibration & Adjustment Function")
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.1 Ext Adjustment Default Weight [Factory O]", values=("1.1.9", "1.1.9.1"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.3 Ext Adjustment User Defined Weight", values=("1.1.9", "1.1.9.3"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.4 Internal Adjustment", values=("1.1.9", "1.1.9.4"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.6 Ext Linearization Default Weight Setup", values=("1.1.9", "1.1.9.6"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.7 Ext Linearization User Assigned Weight", values=("1.1.9", "1.1.9.7"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.8 Set Preload Value", values=("1.1.9", "1.1.9.8"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.9 Delete Preload Value", values=("1.1.9", "1.1.9.9"))
        self.cas_tree.insert(l3_cal, "end", text="1.1.9.10 Calibration Key/Command Blocked", values=("1.1.9", "1.1.9.10"))
        self.cas_tree.insert(l3_cal, "end", text="2.1.9.12 Selection List Path", values=("1.1.9", "2.1.9.12"))
        self.cas_tree.insert(l3_cal, "end", text="3.1.9.18 Define Internal Weight Value Registers", values=("1.1.9", "3.1.9.18"))

        l3_process = self.cas_tree.insert(l2_balance, "end", text="1.1.10 Adjustment Process Pipeline")
        self.cas_tree.insert(l3_process, "end", text="1.1.10.1 Adjust immediately [Factory O]", values=("1.1.10", "1.1.10.1"))
        self.cas_tree.insert(l3_process, "end", text="1.1.10.2 Calibration before adjustment routine", values=("1.1.10", "1.1.10.2"))

        l3_z_range = self.cas_tree.insert(l2_balance, "end", text="1.1.11 Zero Range")
        self.cas_tree.insert(l3_z_range, "end", text="1.1.11.2 2% Maximum Load [Factory O]", values=("1.1.11", "1.1.11.2"))
        self.cas_tree.insert(l3_z_range, "end", text="1.1.11.4 10% Maximum Load", values=("1.1.11", "1.1.11.4"))

        l3_pwr_z = self.cas_tree.insert(l2_balance, "end", text="1.1.12 Zero At Power On")
        self.cas_tree.insert(l3_pwr_z, "end", text="1.1.12.4 10% Max Load [Factory O]", values=("1.1.12", "1.1.12.4"))
        self.cas_tree.insert(l3_pwr_z, "end", text="1.1.12.7 100% Max Load Tracking Range", values=("1.1.12", "1.1.12.7"))

        l3_tare_pwr = self.cas_tree.insert(l2_balance, "end", text="1.1.13 Tare / Zero At Power On")
        self.cas_tree.insert(l3_tare_pwr, "end", text="1.1.13.1 ON [Factory O]", values=("1.1.13", "1.1.13.1"))
        self.cas_tree.insert(l3_tare_pwr, "end", text="1.1.13.2 OFF", values=("1.1.13", "1.1.13.2"))

        l3_rate = self.cas_tree.insert(l2_balance, "end", text="1.1.14 Output Rate Speed")
        for idx, step in enumerate(["Normal [Factory O]", "Fast", "Slow 10Hz", "Moderate 20Hz", "Quick 25Hz", "Very Quick 50Hz", "Maximum 100Hz"], 1):
            self.cas_tree.insert(l3_rate, "end", text=f"1.1.14.{idx} {step}", values=("1.1.14", f"1.1.14.{idx}"))

        l3_isocal = self.cas_tree.insert(l2_balance, "end", text="1.1.15 Auto Calibration / ISOCAL")
        self.cas_tree.insert(l3_isocal, "end", text="1.1.15.1 OFF [Factory O]", values=("1.1.15", "1.1.15.1"))
        self.cas_tree.insert(l3_isocal, "end", text="1.1.15.2 Note Alerts Enabled", values=("1.1.15", "1.1.15.2"))

        # 1.9 General settings
        self.cas_tree.insert(l2_general, "end", text="1.9.1.1 Load Factory Settings Profiles", values=("1.9.1", "1.9.1.1"))
        self.cas_tree.insert(l2_general, "end", text="1.9.1.2 Standby Operational [Factory O]", values=("1.9.1", "1.9.1.2"))

        # --- 2. ACTIVE PRINT MENU HIERARCHY (3.1 - 3.3) --- [cite: 3]
        l2_print_comm = self.cas_tree.insert(l1_print, "end", text="3.1 Communication Parameters", open=True)
        l2_print_param = self.cas_tree.insert(l1_print, "end", text="3.2 Print Parameters", open=True)
        l2_pc_direct = self.cas_tree.insert(l1_print, "end", text="3.3 PC Direct Parameters", open=True)

        l3_p_data = self.cas_tree.insert(l2_print_comm, "end", text="Data Output Sync Trigger")
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.1 Individual value without stability [Factory O]", values=("3.1.1", "3.1.1.1"))
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.2 Individual value after stability Lock", values=("3.1.1", "3.1.1.2"))
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.4 Automatic, without stability stream", values=("3.1.1", "3.1.1.4"))
        self.cas_tree.insert(l3_p_data, "end", text="3.1.1.5 Automatic, after stability window", values=("3.1.1", "3.1.1.5"))

        l3_p_can = self.cas_tree.insert(l2_print_comm, "end", text="Cancel Auto Output")
        self.cas_tree.insert(l3_p_can, "end", text="3.1.2.1 Cancel not possible [Factory O]", values=("3.1.2", "3.1.2.1"))
        self.cas_tree.insert(l3_p_can, "end", text="3.1.2.2 Cancel via print command intercept", values=("3.1.2", "3.1.2.2"))

        l3_p_cyc = self.cas_tree.insert(l2_print_comm, "end", text="Cycle Automatic Output")
        self.cas_tree.insert(l3_p_cyc, "end", text="3.1.3.1 Every value raw block transmission [Factory O]", values=("3.1.3", "3.1.3.1"))
        self.cas_tree.insert(l3_p_cyc, "end", text="3.1.3.2 Every 2nd value structural suppression", values=("3.1.3", "3.1.3.2"))

        l3_p_fmt = self.cas_tree.insert(l2_print_comm, "end", text="Output Format String Block Size")
        self.cas_tree.insert(l3_p_fmt, "end", text="3.1.4.1 16 characters raw metrics output data", values=("3.1.4", "3.1.4.1"))
        self.cas_tree.insert(l3_p_fmt, "end", text="3.1.4.2 22 characters text identifier frame", values=("3.1.4", "3.1.4.2"))

        l3_prt_trig = self.cas_tree.insert(l2_print_param, "end", text="Printout Sync Trigger Path")
        self.cas_tree.insert(l3_prt_trig, "end", text="3.2.1.1 Manual, without stability threshold", values=("3.2.1", "3.2.1.1"))
        self.cas_tree.insert(l3_prt_trig, "end", text="3.2.1.2 Manual, after stability confirmation [O]", values=("3.2.1", "3.2.1.2"))
        self.cas_tree.insert(l3_prt_trig, "end", text="3.2.1.6 Automatic, after load change variance", values=("3.2.1", "3.2.1.6"))

        l3_prt_lfmt = self.cas_tree.insert(l2_print_param, "end", text="Printout Format Structure")
        self.cas_tree.insert(l3_prt_lfmt, "end", text="3.2.2.2 Application, with identification strings", values=("3.2.2", "3.2.2.2"))

        l3_prt_app = self.cas_tree.insert(l2_print_param, "end", text="Printout Appl. Parameters")
        self.cas_tree.insert(l3_prt_app, "end", text="3.2.3.1 Off parameter visibility state", values=("3.2.3", "3.2.3.1"))
        self.cas_tree.insert(l3_prt_app, "end", text="3.2.3.2 All parameters fully written visible", values=("3.2.3", "3.2.3.2"))
        self.cas_tree.insert(l3_prt_app, "end", text="3.2.3.3 Only main parameters critical visible", values=("3.2.3", "3.2.3.3"))

        l3_prt_glp = self.cas_tree.insert(l2_print_param, "end", text="Printout GLP QA Protocol")
        self.cas_tree.insert(l3_prt_glp, "end", text="3.2.4.1 Off profile baseline [Factory O]", values=("3.2.4", "3.2.4.1"))
        self.cas_tree.insert(l3_prt_glp, "end", text="3.2.4.2 Only after verification cal./adjustment", values=("3.2.4", "3.2.4.2"))
        self.cas_tree.insert(l3_prt_glp, "end", text="3.2.4.3 Always on, appended with manual trigger", values=("3.2.4", "3.2.4.3"))

        l3_pc_sep = self.cas_tree.insert(l2_pc_direct, "end", text="Decimal Separator")
        self.cas_tree.insert(l3_pc_sep, "end", text="3.3.1.1 Point separator notation rule [Factory O]", values=("3.3.1", "3.3.1.1"))
        self.cas_tree.insert(l3_pc_sep, "end", text="3.3.1.2 Comma separator alignment rule", values=("3.3.1", "3.3.1.2"))

        l3_pc_out = self.cas_tree.insert(l2_pc_direct, "end", text="Output Format Mode")
        self.cas_tree.insert(l3_pc_out, "end", text="3.3.2.1 Text and numerical value data string [O]", values=("3.3.2", "3.3.2.1"))
        self.cas_tree.insert(l3_pc_out, "end", text="3.3.2.2 Numerical value metric only array size", values=("3.3.2", "3.3.2.2"))

        # --- 3. ACTIVE DEVICE MENU HIERARCHY (2.1 - 2.9) --- [cite: 10, 14, 20]
        l2_dev_i1 = self.cas_tree.insert(l1_device, "end", text="2.1 Interface 1 (RS232)", open=True)
        l2_dev_i2 = self.cas_tree.insert(l1_device, "end", text="2.2 Interface 2 (USB)", open=True)
        l2_dev_add = self.cas_tree.insert(l1_device, "end", text="2.9 Additional Function", open=True)

        l3_i1_proto = self.cas_tree.insert(l2_dev_i1, "end", text="Data Protocol Profile")
        self.cas_tree.insert(l3_i1_proto, "end", text="2.1.1.1 SBI Core Mode [Factory O]", values=("2.1.1", "2.1.1.1"))
        self.cas_tree.insert(l3_i1_proto, "end", text="2.1.1.2 xBPI High Performance Link", values=("2.1.1", "2.1.1.2"))
        self.cas_tree.insert(l3_i1_proto, "end", text="2.1.1.4 SBI 2nd external display panel sync", values=("2.1.1", "2.1.1.4"))
        self.cas_tree.insert(l3_i1_proto, "end", text="2.1.1.7 Universal printer framework (YDP20)", values=("2.1.1", "2.1.1.7"))
        self.cas_tree.insert(l3_i1_proto, "end", text="2.1.1.8 Lab automation printer module (YDP30)", values=("2.1.1", "2.1.1.8"))

        l3_i1_baud = self.cas_tree.insert(l2_dev_i1, "end", text="Baud Rate Interface Speed")
        for idx, baud in [("3","600"), ("4","1200"), ("5","2400"), ("6","4800"), ("7","9600 [O]"), ("8","19200"), ("9","38400"), ("10","576000"), ("11","115200")]:
            self.cas_tree.insert(l3_i1_baud, "end", text=f"2.1.2.{idx} {baud} bps", values=("2.1.2", f"2.1.2.{idx}"))

        l3_i1_par = self.cas_tree.insert(l2_dev_i1, "end", text="Parity Framework Mask")
        self.cas_tree.insert(l3_i1_par, "end", text="2.1.3.3 Odd structural verification [O]", values=("2.1.3", "2.1.3.3"))
        self.cas_tree.insert(l3_i1_par, "end", text="2.1.3.4 Even structural validation check", values=("2.1.3", "2.1.3.4"))
        self.cas_tree.insert(l3_i1_par, "end", text="2.1.3.5 No parity tracking bit buffer", values=("2.1.3", "2.1.3.5"))

        l3_i1_stop = self.cas_tree.insert(l2_dev_i1, "end", text="Stop Bits Layer Size")
        self.cas_tree.insert(l3_i1_stop, "end", text="2.1.4.1 1 stop bit validation frame [O]", values=("2.1.4", "2.1.4.1"))
        self.cas_tree.insert(l3_i1_stop, "end", text="2.1.4.2 2 stop bits validation sequence", values=("2.1.4", "2.1.4.2"))

        l3_i1_hand = self.cas_tree.insert(l2_dev_i1, "end", text="Handshake Hardware Sync Mode")
        self.cas_tree.insert(l3_i1_hand, "end", text="2.1.5.1 Software Handshake protocol stream", values=("2.1.5", "2.1.5.1"))
        self.cas_tree.insert(l3_i1_hand, "end", text="2.1.5.2 Hardware Handshake serial flow line", values=("2.1.5", "2.1.5.2"))
        self.cas_tree.insert(l3_i1_hand, "end", text="2.1.5.3 No handshake synchronization link", values=("2.1.5", "2.1.5.3"))

        l3_i1_bits = self.cas_tree.insert(l2_dev_i1, "end", text="Data Bits Word Structure")
        self.cas_tree.insert(l3_i1_bits, "end", text="2.1.6.1 7 data bits structural character [O]", values=("2.1.6", "2.1.6.1"))
        self.cas_tree.insert(l3_i1_bits, "end", text="2.1.6.2 8 data bits structural character size", values=("2.1.6", "2.1.6.2"))

        # Interface 2 (USB) [cite: 14]
        l3_i2_proto = self.cas_tree.insert(l2_dev_i2, "end", text="Data Protocol Profile")
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.1 SBI Stream Mode Layout", values=("2.2.1", "2.2.1.1"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.2 xBPI High Performance Pipeline Link", values=("2.2.1", "2.2.1.2"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.4 SBI 2nd display auxiliary channel interface", values=("2.2.1", "2.2.1.4"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.6 PC spreadsheet format parsed matrix", values=("2.2.1", "2.2.1.6"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.7 Universal printer layout alignment (YDP20)", values=("2.2.1", "2.2.1.7"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.8 Lab printer layout protocol track (YDP30)", values=("2.2.1", "2.2.1.8"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.9 PC text format baseline frame structure", values=("2.2.1", "2.2.1.9"))
        self.cas_tree.insert(l3_i2_proto, "end", text="2.2.1.10 Off entire communication layer channel", values=("2.2.1", "2.2.1.10"))

        l3_i2_baud = self.cas_tree.insert(l2_dev_i2, "end", text="Baud Rate Processing Clock")
        for idx, baud in [("3","600"), ("4","1200"), ("5","2400"), ("6","4800"), ("7","9600"), ("8","19200"), ("9","38400"), ("10","576000"), ("11","115200")]:
            self.cas_tree.insert(l3_i2_baud, "end", text=f"2.2.2.{idx} {baud} bps", values=("2.2.2", f"2.2.2.{idx}"))

        l3_i2_par = self.cas_tree.insert(l2_dev_i2, "end", text="Parity Mask Settings")
        self.cas_tree.insert(l3_i2_par, "end", text="2.2.3.3 Odd framework check layer", values=("2.2.3", "2.2.3.3"))
        self.cas_tree.insert(l3_i2_par, "end", text="2.2.3.4 Even framework tracking logic", values=("2.2.3", "2.2.3.4"))
        self.cas_tree.insert(l3_i2_par, "end", text="2.2.3.5 No parity tracking allocation", values=("2.2.3", "2.2.3.5"))

        l3_i2_stop = self.cas_tree.insert(l2_dev_i2, "end", text="Number of Stop Bits")
        self.cas_tree.insert(l3_i2_stop, "end", text="2.2.4.1 1 stop bit character block", values=("2.2.4", "2.2.4.1"))
        self.cas_tree.insert(l3_i2_stop, "end", text="2.2.4.2 2 stop bits character layout", values=("2.2.4", "2.2.4.2"))

        l3_i2_hand = self.cas_tree.insert(l2_dev_i2, "end", text="Handshake Protocol")
        self.cas_tree.insert(l3_i2_hand, "end", text="2.2.5.2 Hardware Handshake workflow route", values=("2.2.5", "2.2.5.2"))
        self.cas_tree.insert(l3_i2_hand, "end", text="2.2.5.3 No handshake protocol execution", values=("2.2.5", "2.2.5.3"))

        l3_i2_bits = self.cas_tree.insert(l2_dev_i2, "end", text="Number of Data Bits")
        self.cas_tree.insert(l3_i2_bits, "end", text="2.2.6.1 7 data bits layout structure size", values=("2.2.6", "2.2.6.1"))
        self.cas_tree.insert(l3_i2_bits, "end", text="2.2.6.2 8 data bits layout structure size", values=("2.2.6", "2.2.6.2"))

        l3_i2_det = self.cas_tree.insert(l2_dev_i2, "end", text="Detected Peripheral Link Node")
        self.cas_tree.insert(l3_i2_det, "end", text="2.2.7.0 None/printer/virt com./PC host/input [O]", values=("2.2.7", "2.2.7.0"))

        # 2.9 Additional Function parameters [cite: 20]
        l3_add_menu = self.cas_tree.insert(l2_dev_add, "end", text="Menu Access Operations Matrix")
        self.cas_tree.insert(l3_add_menu, "end", text="2.9.1.1 Menu can be edited parameters actively", values=("2.9.1", "2.9.1.1"))
        self.cas_tree.insert(l3_add_menu, "end", text="2.9.1.2 Menu read only security block status [O]", values=("2.9.1", "2.9.1.2"))

        l3_add_key = self.cas_tree.insert(l2_dev_add, "end", text="Keypad State Isolation Controls")
        self.cas_tree.insert(l3_add_key, "end", text="2.9.3.1 Keys available console interface active [O]", values=("2.9.3", "2.9.3.1"))
        self.cas_tree.insert(l3_add_key, "end", text="2.9.3.2 Keys blocked tracking firmware isolation", values=("2.9.3", "2.9.3.2"))

        l3_add_boot = self.cas_tree.insert(l2_dev_add, "end", text="Start-up Behavior Protocol Strategy")
        self.cas_tree.insert(l3_add_boot, "end", text="2.9.6.3 On/standby (without time loop sequence)", values=("2.9.6", "2.9.6.3"))
        self.cas_tree.insert(l3_add_boot, "end", text="2.9.6.4 Automatic on initialization calibration loop [O]", values=("2.9.6", "2.9.6.4"))

        l3_add_lit = self.cas_tree.insert(l2_dev_add, "end", text="Display Backlight Luminosity Panel")
        self.cas_tree.insert(l3_add_lit, "end", text="2.9.8.1 Off complete illumination array matrix", values=("2.9.8", "2.9.8.1"))
        self.cas_tree.insert(l3_add_lit, "end", text="2.9.8.2 On complete illumination high intensity active [O]", values=("2.9.8", "2.9.8.2"))

        # --- 4. ACTIVE APPLICATION MENU HIERARCHY (4.1 - 4.9) ---
        l2_app_weigh = self.cas_tree.insert(l1_apps, "end", text="4.1 Weighing Only Mode Branches", open=True)
        l2_app_count = self.cas_tree.insert(l1_apps, "end", text="4.3 Counting Application Profile")
        l2_app_pct = self.cas_tree.insert(l1_apps, "end", text="4.4 Percentage Tracking Mode Profile")
        l2_app_net = self.cas_tree.insert(l1_apps, "end", text="4.5 Net Total Component Recipe Profile")
        l2_app_tot = self.cas_tree.insert(l1_apps, "end", text="4.6 Totalizing Storage Accumulation Profile")
        l2_app_anim = self.cas_tree.insert(l1_apps, "end", text="4.7 Animal Balance Core Dynamic Profile")
        l2_app_calc = self.cas_tree.insert(l1_apps, "end", text="4.8 Calculation Multiplication Mathematical")
        l2_app_dens = self.cas_tree.insert(l1_apps, "end", text="4.9 Density Determination Metrology Profile")

        # Leaf node generation allocations for active application routines
        self.cas_tree.insert(l2_app_weigh, "end", text="Trigger dynamic standard weight unit toggle frame", values=("4.1", "Toggle"))
        
        l3_c_res = self.cas_tree.insert(l2_app_count, "end", text="Piece resolution accuracy limit properties")
        self.cas_tree.insert(l3_c_res, "end", text="Normal computing scanning window", values=("4.3.1", "Normal"))
        self.cas_tree.insert(l3_c_res, "end", text="High precision expanded accuracy index", values=("4.3.1", "High"))
        l3_c_ref = self.cas_tree.insert(l2_app_count, "end", text="Reference updating matrix path structure")
        self.cas_tree.insert(l3_c_ref, "end", text="Automatic dynamic optimization adaptive adjustment", values=("4.3.2", "Automatic"))
        self.cas_tree.insert(l3_c_ref, "end", text="Manual profile anchor coordinates pinned", values=("4.3.2", "Manual"))

        l3_p_dec = self.cas_tree.insert(l2_app_pct, "end", text="Decimal precision output resolution bounds")
        self.cas_tree.insert(l3_p_dec, "end", text="1 rounding accuracy position numerical value", values=("4.4", "1"))
        self.cas_tree.insert(l3_p_dec, "end", text="2 rounding accuracy positions numerical value", values=("4.4", "2"))

        l3_n_prt = self.cas_tree.insert(l2_app_net, "end", text="Print component output string frame metadata parsing")
        self.cas_tree.insert(l3_n_prt, "end", text="Component values detailed report block text format", values=("4.5", "Component values"))
        self.cas_tree.insert(l3_n_prt, "end", text="Total accumulation values sum summary textual output", values=("4.5", "Total sum metrics"))

        l3_t_prt = self.cas_tree.insert(l2_app_tot, "end", text="Printout components format output telemetry tracking logs")
        self.cas_tree.insert(l3_t_prt, "end", text="Summary string block profile layout details", values=("4.6", "Summary string"))

        l3_a_act = self.cas_tree.insert(l2_app_anim, "end", text="Animal activity structural measurement vibration dampening filters")
        self.cas_tree.insert(l3_a_act, "end", text="Stable environmental site dampening profile asset configuration", values=("4.7.1", "Stable"))
        self.cas_tree.insert(l3_a_act, "end", text="Hyperactive sensor data tracking signal parsing expansion loop", values=("4.7.1", "Hyperactive"))
        self.cas_tree.insert(l2_app_anim, "end", text="Execute dynamic sensor mathematical signal averaging loop", values=("4.7.2", "Trigger Start"))

        l3_m_met = self.cas_tree.insert(l2_app_calc, "end", text="Calculation pipeline method formula operations mapped")
        self.cas_tree.insert(l3_m_met, "end", text="Multiplication formula engine scaling", values=("4.8.1", "Multiplication"))
        self.cas_tree.insert(l3_m_met, "end", text="Division formula scaling translation", values=("4.8.1", "Division"))
        l3_m_dec = self.cas_tree.insert(l2_app_calc, "end", text="Assigned decimal precision numerical truncation bounds")
        self.cas_tree.insert(l3_m_dec, "end", text="3 decimal positions configuration", values=("4.8.2", "3"))

        l3_d_dec = self.cas_tree.insert(l2_app_dens, "end", text="Assigned decimal precision metrics rounding boundaries")
        self.cas_tree.insert(l3_d_dec, "end", text="4 decimal precision placement pattern specification", values=("4.9", "4"))

    def _render_scrolling_control_ui(self, parent_frame):
        control_canvas = tk.Canvas(parent_frame, bg="#1E293B", bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent_frame, orient="vertical", command=control_canvas.yview)
        
        scrollable_content = ttk.Frame(control_canvas, style="ScrollCard.TFrame", padding=15)
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all"))
        )
        
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
        
        self.message.insert("end", "[CORE_BUS] Multi-protocol configuration registries initialized.\n")
        self.message.configure(state="disabled")

        command_box = ttk.Frame(parent, style="Card.TFrame")
        command_box.pack(fill="x", pady=(12, 0))
        
        self.lbl_mode_indicator = ttk.Label(command_box, text="Active Decoder: RS232 / USB DUAL CONTEXT LINK", font=("Segoe UI", 9, "bold"), foreground="#38BDF8")
        self.lbl_mode_indicator.pack(anchor="w", pady=2)
        
        entry_row = ttk.Frame(command_box, style="TFrame")
        entry_row.pack(fill="x")
        self.command_var = tk.StringVar(value="04 01 09 1E 2C")  
        self.command_entry = ttk.Entry(entry_row, textvariable=self.command_var)
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(entry_row, text="Transmit", style="Action.TButton", command=self.send_command).pack(side="right")

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
        
        # Animal Balance tracking application execution criteria simulation layer overrides filter profiles
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
            
            # Unit Evaluation conversion logic matrix assignment (1.1.7.2 to 1.1.7.23)
            unit_meta = self.unit_map.get(self.active_weight_unit, {"name": "g", "factor": 1.0})
            display_weight = transformed_net_weight * unit_meta["factor"]
            unit_label = f" {unit_meta['name']}"
            
            # Numeric rounding interval calculation execution rules (1.1.8)
            if self.active_accuracy_digits == "1.1.8.7": fmt_pattern = "{:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.3": fmt_pattern = "{:,.3f}"
            elif self.active_accuracy_digits == "1.1.8.4": fmt_pattern = "{:,.2f}"
            elif self.active_accuracy_digits == "1.1.8.5": fmt_pattern = "{:,.1f}"
            elif self.active_accuracy_digits == "1.1.8.14": fmt_pattern = "{:,.5f}"
            else: fmt_pattern = "{:,.4f}"
                
            display_string_output = fmt_pattern.format(display_weight)
            
            # Print suppression context mutations (3.3.2) [cite: 3]
            if self.pc_output_format == "3.3.2.2":
                final_display_frame = f"{display_string_output}{stability_flag}"
            else:
                final_display_frame = f"{display_string_output}{unit_label}{stability_flag}"

            # Decimal swap notation replacement framework (3.3.1) [cite: 3]
            if self.pc_decimal_separator == "3.3.1.2":
                final_display_frame = final_display_frame.replace(".", ",")

            self.display_text.set(final_display_frame)
            self.raw_text.set(f"Transducer Input: {raw_signal:,.4f} g")
            
            if random.random() < 0.02:
                self._write_terminal_log(f"[TX TELEMETRY] App Context: {self.active_app_mode} | Stream Speed: {self.simulation_tick_rate_ms}ms")
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