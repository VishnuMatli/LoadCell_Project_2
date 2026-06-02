# server.py
import tkinter as tk
import socket
import threading
import os
import time
import glob
from tkinter import ttk, filedialog
import struct

# Configuration
SERVER_IP = '0.0.0.0'  # Listen on all interfaces
SERVER_PORT = 5000
BUFFER_SIZE = 4096
DATA_DIR = "adc_data"  # Folder for ADC .txt files

# Define constants for length-prefixing
FILENAME_LENGTH_BYTES = 4   # 4 bytes for filename length (max ~4GB filename, practical for most uses)
FILE_CONTENT_LENGTH_BYTES = 8 # 8 bytes for file content length (max ~16 Exabytes, suitable for very large files)
CONFIG_LENGTH_BYTES = 4 # 4 bytes for configuration message length


class LoadCellServer:
    def __init__(self, root):
        self.root = root
        self.root.title("Load Cell Server")
        self.root.geometry("600x500")
        self.root.configure(bg="#121212")  # Dark futuristic background

        # Apply gradient background
        self.gradient_frame = tk.Frame(root, bg="#121212")
        self.gradient_frame.place(relwidth=1, relheight=1)

        # Title Label
        self.title_label = tk.Label(self.gradient_frame, text="Load Cell Server", font=("Helvetica", 18, "bold"), fg="#00FFFF", bg="#121212")
        self.title_label.pack(pady=10)

        # Mode Selection
        self.label_mode = tk.Label(self.gradient_frame, text="Select Mode:", font=("Helvetica", 12), fg="white", bg="#121212")
        self.label_mode.pack(pady=5)

        self.mode = tk.StringVar(value="interval")  # Default mode: interval-based

        # Custom-styled radio buttons with tick marks inside
        self.radio_interval = tk.Radiobutton(self.gradient_frame, text=" ✔ Send files at fixed intervals", variable=self.mode, value="interval",
                                             font=("Helvetica", 11), fg="white", bg="#1E1E1E", activebackground="#00A2FF", indicatoron=0, width=30, relief="flat",
                                             selectcolor="#1E1E1E", highlightthickness=0, command=self.update_ui_elements)
        self.radio_interval.pack()

        self.radio_freq = tk.Radiobutton(self.gradient_frame, text="   Send specific file by frequency (Hz)", variable=self.mode, value="freq",
                                         font=("Helvetica", 11), fg="white", bg="#1E1E1E", activebackground="#00A2FF", indicatoron=0, width=30, relief="flat",
                                         selectcolor="#1E1E1E", highlightthickness=0, command=self.update_ui_elements)
        self.radio_freq.pack()

        self.radio_select_file = tk.Radiobutton(self.gradient_frame, text="   Select a file and send", variable=self.mode, value="select_file",
                                                font=("Helvetica", 11), fg="white", bg="#1E1E1E", activebackground="#00A2FF", indicatoron=0, width=30, relief="flat",
                                                selectcolor="#1E1E1E", highlightthickness=0, command=self.update_ui_elements)
        self.radio_select_file.pack()

        # Interval Selection
        self.label_interval = tk.Label(self.gradient_frame, text="Select Sending Interval (ms):", font=("Helvetica", 12), fg="white", bg="#121212")
        self.label_interval.pack(pady=5)
        self.interval_var = tk.StringVar(value="20")  # Default 20ms
        self.interval_options = ["1", "2", "5", "10", "20", "50", "100"]
        self.interval_menu = ttk.Combobox(self.gradient_frame, textvariable=self.interval_var, values=self.interval_options, state="readonly")
        self.interval_menu.pack()

        # Frequency Selection
        self.label_freq = tk.Label(self.gradient_frame, text="Enter Frequency (Hz):", font=("Helvetica", 12), fg="white", bg="#121212")
        self.label_freq.pack(pady=5)
        self.freq_entry = ttk.Entry(self.gradient_frame)
        self.freq_entry.insert(0, "50")  # Default frequency
        self.freq_entry.pack()

        # File Selection Button
        self.select_file_button = ttk.Button(self.gradient_frame, text="Select File", command=self.select_file, style="TButton")
        self.select_file_button.pack(pady=10)

        # Start Button
        self.start_button = ttk.Button(self.gradient_frame, text="Start Server", command=self.start_sending, style="TButton")
        self.start_button.pack(pady=10)

        # Stop Button
        self.stop_button = ttk.Button(self.gradient_frame, text="Stop Server", command=self.stop_sending, style="TButton", state="disabled")
        self.stop_button.pack(pady=5)

        # Status Label
        self.status = tk.Label(self.gradient_frame, text="", font=("Helvetica", 12), fg="#00FF00", bg="#121212")
        self.status.pack()

        # Apply styles
        self.apply_styles()

        # Initialize internal state variables
        self.selected_file = None
        self.server_socket = None
        self.client_conn = None
        self.is_sending = False
        self.send_thread = None

        # Update UI elements initially based on default mode
        self.update_ui_elements()
        # Bind the window close event to cleanup function
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def apply_styles(self):
        """Apply futuristic styles to widgets"""
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 12, "bold"), padding=6, relief="flat", background="#00FFFF")
        style.map("TButton",
                  foreground=[('active', 'black'), ('disabled', 'grey')],
                  background=[('active', '#00DDDD'), ('disabled', '#006666')])
        style.configure("TEntry", font=("Helvetica", 12), padding=5)
        style.configure("TCombobox", font=("Helvetica", 12), padding=5)

    def update_ui_elements(self):
        """Update tick mark inside the selected mode and enable/disable inputs"""
        selected_mode = self.mode.get()

        self.radio_interval.config(text=" ✔ Send files at fixed intervals" if selected_mode == "interval" else "   Send files at fixed intervals")
        self.radio_freq.config(text=" ✔ Send specific file by frequency (Hz)" if selected_mode == "freq" else "   Send specific file by frequency (Hz)")
        self.radio_select_file.config(text=" ✔ Select a file and send" if selected_mode == "select_file" else "   Select a file and send")

        # Enable/disable controls based on selected mode
        if selected_mode == "interval":
            self.interval_menu.config(state="readonly")
            self.freq_entry.config(state="disabled")
            self.select_file_button.config(state="disabled")
        elif selected_mode == "freq":
            self.interval_menu.config(state="disabled")
            self.freq_entry.config(state="normal")
            self.select_file_button.config(state="disabled")
        elif selected_mode == "select_file":
            self.interval_menu.config(state="disabled")
            self.freq_entry.config(state="disabled")
            self.select_file_button.config(state="normal")

    def select_file(self):
        """Open file dialog to select a file"""
        self.selected_file = filedialog.askopenfilename(title="Select a File", filetypes=[("Text Files", "*.txt")])
        if self.selected_file:
            self.status.config(text=f"Selected File: {os.path.basename(self.selected_file)}")
        else:
            self.status.config(text="No file selected.")

    def start_sending(self):
        """Starts the file sending process in a separate thread."""
        if self.is_sending:
            self.status.config(text="Already sending...")
            return

        # Ensure any previous connections are fully closed before starting new one
        self._cleanup_connections()

        self.is_sending = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.send_thread = threading.Thread(target=self._send_files_thread, daemon=True)
        self.send_thread.start()

    def stop_sending(self):
        """Stops the file sending process and cleans up connections."""
        if not self.is_sending:
            self.status.config(text="Not currently sending.")
            return

        self.is_sending = False # Signal the thread to stop
        self.status.config(text="Stopping sending...")
        self.stop_button.config(state="disabled")
        self.start_button.config(state="normal")

        # Give the thread a moment to recognize the stop flag and close gracefully
        # If it doesn\'t close promptly, force close sockets.
        if self.send_thread and self.send_thread.is_alive():
            # A small delay to allow the thread to self-terminate if it's in a safe state
            time.sleep(0.1)

        self._cleanup_connections() # Force close any lingering sockets

    def on_closing(self):
        """Handles the window closing event to ensure graceful shutdown."""
        self.stop_sending()
        self.root.destroy()

    def _cleanup_connections(self):
        """Closes server and client sockets cleanly."""
        if self.client_conn:
            try:
                # Attempt to gracefully shut down both read and write sides
                self.client_conn.shutdown(socket.SHUT_RDWR)
                self.client_conn.close()
                print("[SERVER] Client connection closed.")
            except OSError as e:
                print(f"[SERVER] Error closing client connection: {e}")
            finally:
                self.client_conn = None

        if self.server_socket:
            try:
                # Shutdown and close the listening socket
                self.server_socket.shutdown(socket.SHUT_RDWR)
                self.server_socket.close()
                print("[SERVER] Server listening socket closed.")
            except OSError as e:
                print(f"[SERVER] Error closing server socket: {e}")
            finally:
                self.server_socket = None

    def _send_files_thread(self):
        """
        Handles the sending of files to the client, based on the selected mode.
        Runs in a separate thread.
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allows immediate reuse of address
            self.server_socket.bind((SERVER_IP, SERVER_PORT))
            self.server_socket.listen(1)
            self.status.config(text="Waiting for client connection...")

            # Set a timeout for accept to allow checking self.is_sending
            self.server_socket.settimeout(1.0) # 1 second timeout for accept

            while self.is_sending: # Keep trying to accept as long as sending is active
                try:
                    conn, addr = self.server_socket.accept()
                    self.client_conn = conn # Store the active client connection
                    break # Connection accepted, exit loop
                except socket.timeout:
                    # No connection within timeout, check if sending should stop
                    if not self.is_sending:
                        print("[SERVER] Server accept timed out, stopping.")
                        self.status.config(text="Sending stopped.")
                        return # Exit thread if stop requested
                    continue # Continue waiting for connection
            
            if not self.is_sending: # Check if loop exited due to stop flag
                print("[SERVER] Sending stopped before connection was established.")
                self.status.config(text="Sending stopped.")
                return

            self.status.config(text=f"Connected to {addr}. Sending data...")

            # Ensure the data folder exists, even if not creating dummy data
            if not os.path.exists(DATA_DIR):
                os.makedirs(DATA_DIR)
                print(f"Created data folder: {DATA_DIR} (was missing)")

            all_files_in_folder = sorted(glob.glob(os.path.join(DATA_DIR, "*.txt")))
            if not all_files_in_folder:
                self.status.config(text=f"Error: No .txt files found in '{DATA_DIR}'!")
                print(f"[SERVER] Error: No .txt files found in '{DATA_DIR}'.")
                self._send_file(self.client_conn, None) # Send EOT or error signal to client
                return
            
            # The client is no longer requesting a file.
            # The server will now send a single file based on the GUI selection.

            selected_mode = self.mode.get()
            if selected_mode == "interval":
                self._send_files_at_interval(self.client_conn, all_files_in_folder)
            elif selected_mode == "freq":
                self._send_file_by_frequency(self.client_conn, all_files_in_folder)
            elif selected_mode == "select_file":
                self._send_selected_file(self.client_conn)
            
            if self.is_sending: # Only update status if not explicitly stopped
                self.status.config(text="Finished sending files.")

        except Exception as error:
            self.status.config(text=f"Error: {str(error)}")
            print(f"[*] Exception in _send_files_thread: {error}")
        finally:
            self.is_sending = False
            self._cleanup_connections() # Ensure sockets are closed
            # Re-enable start button and disable stop button on thread completion in main GUI thread
            self.root.after(100, lambda: self.start_button.config(state="normal"))
            self.root.after(100, lambda: self.stop_button.config(state="disabled"))


    def _send_files_at_interval(self, connection, all_files):
        """
        Sends all text files in the data folder at a fixed interval to the client.
        """
        for filename in all_files:
            if not self.is_sending: # Check stop flag before sending each file
                print("[SERVER] Interval sending stopped by user.")
                break
            
            self.status.config(text=f"Sending: {os.path.basename(filename)}")
            self._send_file(connection, filename)
            
            if not self.is_sending: # Check again after sending
                break
            
            try:
                interval_ms = int(self.interval_var.get())
                time.sleep(interval_ms / 1000.0)
            except (ValueError, TypeError):
                print("Invalid interval, defaulting to 1 second.")
                time.sleep(1)

        if self.is_sending: # Only send empty file if not stopped
            self._send_file(connection, None) # Signal end of interval files

    def _send_file_by_frequency(self, connection, all_files):
        """
        Sends a specific file based on the entered frequency.
        """
        frequency = self.freq_entry.get()
        matched_files = [f for f in all_files if f"hz{frequency}" in os.path.basename(f)]

        if not matched_files:
            self.status.config(text=f"No file found for {frequency} Hz")
            self._send_file(connection, None, is_error=True) # Signal error to client
            return

        # Send the file
        if self.is_sending:
            filename = matched_files[0]
            self.status.config(text=f"Sending frequency file: {os.path.basename(filename)}")
            self._send_file(connection, filename)
        
        self._send_file(connection, None) # Signal end of files in this mode


    def _send_selected_file(self, connection):
        """
        Sends the file selected by the user.
        """
        if not self.selected_file or not os.path.exists(self.selected_file):
            self.status.config(text="No file selected or file does not exist!")
            self._send_file(connection, None, is_error=True)
            return

        if self.is_sending:
            self.status.config(text=f"Sending selected file: {os.path.basename(self.selected_file)}")
            self._send_file(connection, self.selected_file)
        
        self._send_file(connection, None) # Signal end of files in this mode


    def _send_file(self, connection, filepath, is_error=False):
        """
        Sends the contents of a file to the client with a header.
        If filepath is None, sends an end-of-transmission signal.
        """
        try:
            if is_error:
                connection.sendall(b"FILE_NOT_FOUND\n")
                connection.sendall(b"0\n")
                print(f"[SERVER] Sent 'FILE_NOT_FOUND' signal.")
                return

            if filepath is None:
                connection.sendall(b"END_OF_TRANSMISSION\n")
                connection.sendall(b"0\n")
                print("[SERVER] Sent 'END_OF_TRANSMISSION' signal.")
                return

            with open(filepath, 'rb') as f:
                file_data = f.read()
            
            file_size = len(file_data)
            
            # Send the header
            connection.sendall(b"FILE_FOUND\n")
            time.sleep(0.1) # Small delay to prevent header and size from merging
            connection.sendall(str(file_size).encode('utf-8') + b'\n')
            time.sleep(0.1)
            
            print(f"[SERVER] Sent header for file '{os.path.basename(filepath)}', size: {file_size} bytes")
            
            # Send the file content
            connection.sendall(file_data)
            print(f"[SERVER] Sent file content.")

        except BrokenPipeError:
            print(f"[SERVER] Client disconnected.")
            self.is_sending = False
        except Exception as error:
            print(f"[SERVER] Error in _send_file for '{filepath}': {error}")
            self.status.config(text=f"Error sending file: {error}")
            self.is_sending = False


if __name__ == "__main__":
    if not os.path.exists(DATA_DIR):
        print(f"[*] Data directory '{DATA_DIR}' not found. Creating it now.")
        os.makedirs(DATA_DIR)
        print(f"[*] Please place your '.txt' ADC data files inside the '{DATA_DIR}' directory.")
        print(f"[*] Exiting. Re-run this program after adding your data files.")
        exit()

    root = tk.Tk()
    app = LoadCellServer(root)
    root.mainloop()
