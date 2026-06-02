# Windowing Methods Implementation Guide

## ✅ Completed Implementation

All 5 windowing methods have been successfully implemented with **CMSIS-DSP library** support:

### **Window Types Implemented**

| Window | Formula | Characteristics | Best For |
|--------|---------|-----------------|----------|
| **Triangular** | `1.0 - 2.0*\|n - (N-1)/2\| / (N-1)` | Moderate spectral leakage reduction | General purpose |
| **Rectangular** | `1.0` (all ones) | Minimal leakage for sinusoids, poor side lobes | Sinusoidal signals |
| **Hamming** | `0.54 - 0.46*cos(2π*n/(N-1))` | Good leakage reduction, better side lobes | Most common choice |
| **Hanning** | `0.5 - 0.5*cos(2π*n/(N-1))` | Better side lobe rolloff than Hamming | Improved spectral performance |
| **Blackman** | `0.42 - 0.5*cos(...) + 0.08*cos(...)` | Excellent side lobe suppression | Very low side lobes |

---

## 📁 Files Created

### **Program Files (One per Window Type)**
- ✅ `signal_analyzer_triangular.c` - Triangular window
- ✅ `signal_analyzer_rectangular.c` - Rectangular window  
- ✅ `signal_analyzer_hamming.c` - Hamming window
- ✅ `signal_analyzer_hanning.c` - Hanning window
- ✅ `signal_analyzer_blackman.c` - Blackman window

### **Build System**
- ✅ `Makefile` - Automatic compilation for all variants
- ✅ `signal_analyzer_fixed.c.backup` - Original backup

---

## 🛠️ Compilation Instructions

### **Compile All Variants**
```bash
make all
```

Output:
```
[Compiling] TRIANGULAR window variant...
✓ signal_analyzer_triangular created
[Compiling] RECTANGULAR window variant...
✓ signal_analyzer_rectangular created
[Compiling] HAMMING window variant...
✓ signal_analyzer_hamming created
[Compiling] HANNING window variant...
✓ signal_analyzer_hanning created
[Compiling] BLACKMAN window variant...
✓ signal_analyzer_blackman created

✓ All windowing variants compiled successfully!
```

### **Compile Individual Variant**
```bash
make triangular
# or
make rectangular
# or
make hamming
# or
make hanning
# or
make blackman
```

### **View Help**
```bash
make help
```

### **Clean Compiled Files**
```bash
make clean
```

---

## 🚀 Usage Examples

### **Run Triangular Window**
```bash
./signal_analyzer_triangular adc_data/535g20250502pm427ms20hz69.txt
```

Output:
```
[DSP_TRIANGULAR] ========================================
[DSP_TRIANGULAR] Analyzing file: adc_data/535g20250502pm427ms20hz69.txt
[DSP_TRIANGULAR] Window Type: TRIANGULAR
[DSP_TRIANGULAR] Cutoff Frequency: 10.00 Hz
[DSP_TRIANGULAR] ========================================
[DSP_TRIANGULAR] Generating FIR coefficients with TRIANGULAR window
[DSP_TRIANGULAR] Cutoff: 10.00 Hz, Sampling: 1000.00 Hz, Normalized fc: 0.0100
[DSP_TRIANGULAR] FIR coefficients generated and normalized
[DSP_TRIANGULAR] Read 3542 ADC samples from file
[DSP_TRIANGULAR] Normalized ADC values to weights
[DSP_TRIANGULAR] FIR filtering completed
[DSP_TRIANGULAR] Filtered data saved to: filtered_triangular_535g20250502pm427ms20hz69.txt
[DSP_TRIANGULAR] ========================================
[DSP_TRIANGULAR] Analysis complete!
[DSP_TRIANGULAR] ========================================
```

### **Run Rectangular Window**
```bash
./signal_analyzer_rectangular adc_data/535g20250502pm427ms20hz69.txt
```

### **Run Hamming Window**
```bash
./signal_analyzer_hamming adc_data/535g20250502pm427ms20hz69.txt
```

### **Run Hanning Window**
```bash
./signal_analyzer_hanning adc_data/535g20250502pm427ms20hz69.txt
```

### **Run Blackman Window**
```bash
./signal_analyzer_blackman adc_data/535g20250502pm427ms20hz69.txt
```

---

## 📊 Output Files

Each program creates a filtered output file with the window name prefix:

```
filtered_triangular_<original_filename>.txt
filtered_rectangular_<original_filename>.txt
filtered_hamming_<original_filename>.txt
filtered_hanning_<original_filename>.txt
filtered_blackman_<original_filename>.txt
```

Example:
```
filtered_triangular_535g20250502pm427ms20hz69.txt
filtered_rectangular_535g20250502pm427ms20hz69.txt
filtered_hamming_535g20250502pm427ms20hz69.txt
filtered_hanning_535g20250502pm427ms20hz69.txt
filtered_blackman_535g20250502pm427ms20hz69.txt
```

---

## 📝 Configuration

Edit cutoff frequency and sampling rate in the source files:

```c
#define CUTOFF_FREQ 10.0f      // Cutoff frequency in Hz
#define SAMPLING_FREQ 1000.0f  // Sampling frequency in Hz
#define NUMTAPS 51             // Number of FIR filter taps
```

Then recompile:
```bash
make clean
make all
```

---

## 🔧 Using with new_run.sh

To use different windowing methods with `new_run.sh`, modify line 12:

```bash
# For Triangular Window:
C_PROGRAM="./signal_analyzer_triangular"

# For Rectangular Window:
C_PROGRAM="./signal_analyzer_rectangular"

# For Hamming Window:
C_PROGRAM="./signal_analyzer_hamming"

# For Hanning Window:
C_PROGRAM="./signal_analyzer_hanning"

# For Blackman Window:
C_PROGRAM="./signal_analyzer_blackman"
```

Then run:
```bash
./new_run.sh
```

---

## 📈 Comparison Workflow

**Process same file with all windows:**

```bash
# Compile all
make all

# Process with each window
./signal_analyzer_triangular adc_data/sample.txt
./signal_analyzer_rectangular adc_data/sample.txt
./signal_analyzer_hamming adc_data/sample.txt
./signal_analyzer_hanning adc_data/sample.txt
./signal_analyzer_blackman adc_data/sample.txt

# Results in:
# filtered_triangular_sample.txt
# filtered_rectangular_sample.txt
# filtered_hamming_sample.txt
# filtered_hanning_sample.txt
# filtered_blackman_sample.txt

# View with main_plot_program.py to compare
python3 main_plot_program.py sample.txt
```

---

## 🔬 Technical Details

### **All Programs Use:**
- ✅ CMSIS-DSP Library (`arm_fir_*` functions)
- ✅ Dynamic FIR coefficient generation
- ✅ Window function applied to sinc function
- ✅ Coefficient normalization for unity gain at DC
- ✅ Same calibration constants as original
- ✅ Identical ADC normalization
- ✅ Same data I/O format

### **Key Functions (All Variants)**
```c
generate_fir_coeffs_<window_type>()  // Window-specific coefficient generation
normalize_to_weights()               // ADC normalization (same in all)
fir_filter()                         // CMSIS-DSP FIR filtering (same in all)
save_data()                          // Output file saving (same in all)
```

---

## 🎯 Quick Start

### **Step 1: Compile All Variants**
```bash
make all
```

### **Step 2: Process Your Data**
```bash
./signal_analyzer_triangular adc_data/your_file.txt
```

### **Step 3: View Results**
```bash
python3 main_plot_program.py your_file.txt
```

---

## 📚 References

### **Window Functions:**
- **Triangular**: Also called Bartlett, linear taper
- **Rectangular**: No windowing, Boxcar window
- **Hamming**: Optimized to minimize side lobes at ±43dB
- **Hanning**: Better side lobe rolloff (-18dB/octave vs -6dB for Hamming)
- **Blackman**: Multi-term window, excellent side lobe suppression (-58dB)

### **FIR Filter Design:**
- Uses Parks-McClellan equiripple approximation via sinc + window
- 51 taps (NUMTAPS = 51)
- Cutoff frequency: 10 Hz
- Sampling frequency: 1000 Hz

---

## ✨ Summary

| Feature | Status |
|---------|--------|
| Triangular Window | ✅ Implemented |
| Rectangular Window | ✅ Implemented |
| Hamming Window | ✅ Implemented |
| Hanning Window | ✅ Implemented |
| Blackman Window | ✅ Implemented |
| CMSIS-DSP Integration | ✅ Complete |
| Makefile Build System | ✅ Complete |
| Output File Naming | ✅ Automatic |
| Standalone Programs | ✅ Each has own executable |
| Original Backup | ✅ signal_analyzer_fixed.c.backup |

---

Generated: 2026-05-18
