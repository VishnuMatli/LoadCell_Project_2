# CMS Codebase Analysis Report

## Executive Summary
Your codebase contains a complete signal processing pipeline with server-client architecture, DSP filtering, and visualization. The system reads ADC load cell data, applies dynamic FIR filtering with FFT analysis, and provides real-time visualization.

---

## 1. SERVER FILES COMPARISON

### **server.py** ✅ LATEST & WORKING
- **Status**: Advanced, feature-complete
- **Features**:
  - Tkinter GUI with dark theme
  - 3 sending modes:
    1. **Interval mode**: Send all files at fixed intervals (1-100ms)
    2. **Frequency mode**: Send specific file by frequency (Hz)
    3. **File selection mode**: Manually select and send individual files
  - Socket-based transmission with proper cleanup
  - Length-prefixed protocol (4-byte filename, 8-byte file size)
  - Event-based socket handling with timeouts
  - Thread-safe operation
  - Graceful shutdown handling
- **Port**: 5000
- **Data Directory**: `adc_data/`

### **Server2.py** 
- **Status**: Basic, index-based protocol
- **Features**:
  - Simple socket server
  - Client requests files by index (0, 1, 2...)
  - No GUI
  - No interval control
- **Port**: 5000
- **Protocol**: 4-byte index request → file sent with length prefix
- **Verdict**: Superseded by server.py (less flexible)

---

## 2. CLIENT ANALYSIS

### **Server-Connected Clients:**

#### **filter_client.c** ✅ RECOMMENDED
- **Status**: Advanced dynamic filtering
- **Features**:
  - Connects to server (port 5000)
  - Receives data files via socket
  - Dynamic FIR filter with 64 taps
  - **FFT-based cutoff detection**: Analyzes signal spectrum and adjusts filter cutoff to 90% energy threshold
  - Samples into 256-point buffer
  - Applies Hamming window to FIR coefficients
  - Real-time filtering with single sample processing (BLOCK_SIZE=1)
- **Sampling Rate**: 1000 Hz (configurable)
- **Window**: Hamming (built-in)

#### **filter_client2.c**
- **Status**: Improved version of filter_client.c
- **Differences**:
  - More stable initial response (uses fixed 50Hz cutoff initially)
  - Sliding window FFT update (every FFT_SIZE/2 samples)
  - Better numerical stability in cutoff calculation
- **Verdict**: Better than filter_client.c (more robust)

#### **weigh.c**
- **Status**: File reception client
- **Features**:
  - Connects to server (port 9999)
  - Receives files with standard length-prefix protocol
  - Saves to `recv_data/` folder
  - Basic error handling
- **Verdict**: Simple receiver, no processing

#### **weigh2.c**
- **Status**: Improved weigh.c
- **Features**:
  - Connects to server (port 5000)
  - Iterative file requests (index-based)
  - Saves to `client_files/` folder
  - Cleaner socket handling
- **Verdict**: More flexible than weigh.c

### **Standalone Client:**

#### **signal_analyzer_fixed.c** ✅ STANDALONE (NO SERVER NEEDED)
- **Status**: Fully independent DSP processor
- **Input**: Direct file path as command-line argument
- **Processing**:
  1. Reads ADC integers from text file
  2. Normalizes to weights using calibration: `(adc/2^31 - ZERO_CAL) / SCALE_CAL`
  3. Applies static FIR filter (51 taps)
  4. Outputs filtered data to `filtered_<filename>`
- **Calibration Constants**:
  - ZERO_CAL = 0.01823035255075
  - SCALE_CAL = 0.00000451794631
- **FIR Taps**: Pre-calculated 51-tap coefficients
- **Usage**: `./signal_analyzer_fixed <input_file.txt>`
- **Verdict**: Perfect for batch processing without server

---

## 3. PLOTTING & VISUALIZATION

### **plot_filter.py**
- Static plot from single file
- Hardcoded file path
- Minimal features
- **Status**: Deprecated

### **plot2.py**
- Interactive plotting with matplotlib
- Radio buttons for speed control (1-100ms)
- Pause/Resume/Exit buttons
- Loads pre-processed CSV data
- **Status**: Basic but functional

### **main_plot_program.py** ✅ RECOMMENDED
- **Status**: Advanced live plotting system
- **Features**:
  - 3-panel display:
    1. Raw ADC data (time domain)
    2. Filtered data (time domain)
    3. FFT spectrum (frequency domain)
  - Live animation with configurable speed
  - FFT with **Hamming window** applied
  - Single-sided spectrum scaling (corrected DC and Nyquist)
  - Dynamic Y-axis scaling
  - Scrolling window visualization (500-sample window)
  - Analysis text overlay
  - Pause/Resume/Exit controls
- **Windowing**: Hamming window via `np.hamming(window_size)`
- **Sampling Rate**: 50 Hz (for frequency axis)
- **Input**: Loads pre-processed CSV files from `output_data/`

---

## 7. WINDOWING METHODS STATUS

### **✅ IMPLEMENTED:**

| Window Type | Location | Implementation |
|------------|----------|-----------------|
| **Hamming** | filter_client.c (L63) | `0.54 - 0.46*cos(2π*n/(N-1))` |
| **Hamming** | filter_client2.c (L58) | Same as above |
| **Hamming** | main_plot_program.py (L271) | `np.hamming(window_size)` |

### **❌ NOT IMPLEMENTED (Need to add):**

| Window Type | Formula | Use Case |
|------------|---------|----------|
| **Rectangular** | All 1.0 | Minimal spectral leakage for sinusoids, poor side lobes |
| **Triangular** | `1 - 2*\|n - (N-1)/2\| / (N-1)` | Moderate performance, symmetric |
| **Hanning** | `0.5 - 0.5*cos(2π*n/(N-1))` | Better side lobe rolloff than Hamming |
| **Blackman** | `0.42 - 0.5*cos(...) + 0.08*cos(...)` | Excellent side lobe suppression, wider main lobe |
| **Kaiser** | Requires Bessel function | Adjustable trade-off via beta parameter |

### **Current Window Usage:**
- **FIR Filter Design** (filter_client.c, filter_client2.c):
  - Window applied to FIR coefficients during design
  - Reduces spectral leakage in filtering
  
- **FFT Analysis** (main_plot_program.py):
  - Window applied to input data before FFT
  - Reduces spectral leakage in frequency analysis

---

## 8. WORKFLOW & ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                    ADC DATA                              │
│           (adc_data/*.txt files)                         │
└─────────────────────────────────────────────────────────┘
                          │
                ┌─────────┴──────────┐
                │                    │
        ┌───────▼────────┐   ┌──────▼──────────┐
        │   SERVER.PY    │   │ signal_analyzer │
        │   (GUI Server) │   │  _fixed.c       │
        └───────┬────────┘   │ (Standalone)    │
                │            └──────┬──────────┘
                │                   │
        ┌───────▼──────────────┐    │
        │  CLIENT SELECTION    │    │
        │ ─────────────────    │    │
        │ • filter_client2.c   │    │
        │ • weigh2.c           │    │
        │ • weigh.c            │    │
        └───────┬──────────────┘    │
                │                   │
        ┌───────▼──────────────┐    │
        │ DSP PROCESSING       │    │
        │ ──────────────       │    │
        │ • FIR Filter         │    │
        │ • FFT Analysis       │    │
        │ • Calibration        │    │
        └───────┬──────────────┘    │
                │                   │
        ┌───────▼──────────────┐    │
        │ OUTPUT DATA          │◄───┘
        │ • output_data/*.csv  │
        │ • analysis_results/* │
        └───────┬──────────────┘
                │
        ┌───────▼──────────────┐
        │ VISUALIZATION        │
        │ ──────────────       │
        │ • main_plot_...py    │
        │ • Live animation     │
        │ • FFT spectrum       │
        └──────────────────────┘
```

---

## 6. AUTOMATION SCRIPT: new_run.sh

### **Overview:**
Complete end-to-end automation script that combines signal processing and visualization in one command.

### **What it does:**
1. Changes to working directory (`/home/vishnu/Documents/CMS`)
2. Runs `signal_analyzer_fixed` with interactive prompts
3. Monitors exit status for errors
4. Activates Python virtual environment (`venv`)
5. Auto-detects latest processed output file
6. Extracts original filename from `raw_weights_*.csv`
7. Launches `main_plot_program.py` with detected file
8. Deactivates venv on completion

### **Usage:**
```bash
./new_run.sh
# When prompted by signal_analyzer_fixed:
# - Enter directory: adc_data
# - Select file number: (choose your file)
# - Script will then automatically show the plot
```

### **Prerequisites:**
- Python venv must exist at `./venv`
- Required packages: matplotlib, numpy
- Setup (one-time):
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install matplotlib numpy
  ```

### **Output Flow:**
```
signal_analyzer_fixed input
         ↓
Processes ADC data
         ↓
Creates output_data/raw_weights_*.csv
         ↓
Script detects newest file
         ↓
main_plot_program.py launches automatically
         ↓
Live plot displayed
```

### **Configuration:**
Edit `new_run.sh` to change:
- Line 9: `WORKING_DIR="/home/vishnu/Documents/CMS"` (your working path)
- Line 12: `C_PROGRAM="./signal_analyzer_fixed"` (C executable)
- Line 15: `PYTHON_SCRIPT="main_plot_program.py"` (Python script)

---

## 6. RECOMMENDED CONFIGURATION

### **AUTOMATED WORKFLOW (✅ RECOMMENDED - Easiest):**
```bash
# One-command automation for processing and visualization
bash new_run.sh
# This script:
# 1. Runs signal_analyzer_fixed (asks for file selection)
# 2. Activates Python venv automatically
# 3. Detects latest output file
# 4. Launches main_plot_program.py automatically
# 5. Full pipeline: Process → Plot → Display
```

### **For Real-Time Streaming (Advanced):**
```bash
# Terminal 1: Start server
python3 server.py

# Terminal 2: Start client
./filter_client2  # Best dynamic filtering

# Terminal 3: View results (after some data)
python3 main_plot_program.py <filename.txt>
```

### **For Batch Processing (Manual):**
```bash
# Process without server
./signal_analyzer_fixed adc_data/your_file.txt
```

### **For Live Visualization (Manual):**
```bash
python3 main_plot_program.py 535g20250502pm427ms20hz69.txt
```

---

## 9. KEY TECHNICAL SPECIFICATIONS

| Parameter | Value | Location |
|-----------|-------|----------|
| **FFT Size** | 256 | filter_client.c:10 |
| **FIR Taps** | 64 (filter_client) / 51 (signal_analyzer) | Various |
| **Sampling Rate** | 1000 Hz (DSP) / 50 Hz (plot) | Configurable |
| **Energy Threshold** | 0.9 (90%) | filter_client.c:11 |
| **Block Size** | 1 | filter_client.c:9 |
| **Plot Window** | 500 samples | main_plot_program.py:25 |
| **Server Port** | 5000 | server.py:10 |

---

## 10. FILES NOT INCLUDED IN ANALYSIS

- **filter.c**: Only contains comments/prompt, no implementation
- **arm_bitreversal2.c**: Utility function for FFT, already in CMSIS-DSP
- **plot_filter.py**: Deprecated/static plotting
- **plot2.py**: Older interactive version (superseded by main_plot_program.py)

---

## 11. RECOMMENDATIONS

### **Immediate Actions:**
1. ✅ Use **server.py** for GUI-based server (latest)
2. ✅ Use **filter_client2.c** or **filter_client.c** for dynamic filtering
3. ✅ Use **signal_analyzer_fixed.c** for standalone processing
4. ✅ Use **main_plot_program.py** for visualization

### **Future Enhancements:**
1. **Add Windowing Options:**
   - Implement menu in server.py to select window type
   - Add to filter_client for FIR design window selection
   - Add to main_plot_program.py for FFT window selection

2. **Sample Implementation for Rectangular Window:**
   ```c
   // In filter_client.c, replace Hamming with:
   float32_t window = 1.0f;  // Rectangular window (all ones)
   coeffs[n] = sinc_val * window;
   ```

3. **Sample Implementation for Triangular Window:**
   ```c
   float32_t alpha = (num_taps - 1) / 2.0f;
   float32_t window = 1.0f - 2.0f * fabsf(n - alpha) / (num_taps - 1);
   coeffs[n] = sinc_val * window;
   ```

4. **Multi-Window Support in Python:**
   ```python
   windows = {
       'hamming': np.hamming,
       'hanning': np.hanning,
       'blackman': np.blackman,
       'rectangular': np.ones,
       'triangular': np.bartlett
   }
   ```

---

## 12. SUMMARY TABLE

| Component | Latest Version | Type | Status |
|-----------|-----------------|------|--------|
| **Automation** | new_run.sh | Shell Script | ✅ **RECOMMENDED FIRST** |
| Server | server.py | Advanced GUI | ✅ RECOMMENDED |
| Client (Network) | filter_client2.c | Dynamic DSP | ✅ RECOMMENDED |
| Client (Standalone) | signal_analyzer_fixed.c | Batch DSP | ✅ RECOMMENDED |
| Visualization | main_plot_program.py | Live FFT Plot | ✅ RECOMMENDED |
| Windowing | Hamming | FIR + FFT | ✅ Implemented |
| Additional Windows | (None) | - | ❌ Need Implementation |

---

## 13. QUESTIONS ANSWERED:

1. **Latest Server**: `server.py` with GUI (most feature-rich)
2. **Matching Clients**: `filter_client2.c` (best) or `filter_client.c`
3. **Standalone Client**: `signal_analyzer_fixed.c` (no server needed)
4. **Windowing**: Only **Hamming** window is currently implemented
5. **Missing Windows**: Triangular, Rectangular, Hanning, Blackman, Kaiser (ready for implementation)
6. **Automation Script**: `new_run.sh` provides complete end-to-end workflow

---

Generated: 2026-05-18
