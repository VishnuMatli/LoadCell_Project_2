# CMS DSP Signal Processing Toolkit

This repository contains a complete CMS-based ADC signal processing workflow:

- multiple standalone FIR analyzer programs
- automated batch filtering for every input file
- a Tkinter/Matplotlib GUI for browsing raw vs filtered data
- a plot exporter that saves comparison images and bandwidth summaries

The project is focused on experimenting with different FIR design and windowing methods on ADC load-cell data.

## Main Features

- Batch-process every `.txt` file in `adc_data/`
- Generate filtered outputs for 9 methods:
  - triangular
  - rectangular
  - hamming
  - hanning
  - blackman
  - kaiser
  - parks_mcclellan
  - frequency_sampling
  - least_squares
- View raw and filtered plots in a GUI with file/window/speed dropdowns
- Export one full comparison plot per file per method
- Save an Excel bandwidth summary for all exported plots

## Repository Layout

- `adc_data/` - input ADC text files
- `output/` - filtered outputs grouped by method
- `plots/` - exported PNG plots grouped by method
- `main_plot_program.py` - interactive plotting GUI
- `save_all_plots.py` - batch plot exporter + progress GUI + Excel summary
- `weigh_cell_simulator.py` - virtual weigh cell simulator with scaling, tare, zero-scaling, and machine status blinking
- `new_run.sh` - automation script for filtering all files and launching the GUI
- `Makefile` - builds all analyzer executables
- `signal_analyzer_*.c` - one standalone C analyzer per filtering method

## Requirements

- Python 3
- `numpy`
- `matplotlib`
- Tkinter
- GCC or Clang
- CMSIS-DSP sources present in `CMSIS-DSP/`
- CMSIS core headers present in `CMSIS_5/`

The repository already includes a Python virtual environment at `venv/` in the current setup.

## Quick Start

### 1. Build all analyzers

```bash
make all
```

### 2. Batch-process every input file

```bash
./new_run.sh
```

This script:

- finds every `.txt` file in `adc_data/`
- runs all 9 analyzers on each file
- stores filtered outputs in `output/<method>/`
- launches `main_plot_program.py` after processing

### 3. Open the interactive GUI directly

```bash
source venv/bin/activate
python main_plot_program.py
```

You can then choose:

- input file
- filtering method
- plot speed

## Export Plots and Bandwidths

To save full-size plots for every file and window method, run:

```bash
source venv/bin/activate
python save_all_plots.py
```

This creates:

- PNG files in `plots/<method>/`
- `plots/bandwidth_summary.xlsx`

The Excel sheet stores:

- file name
- method name
- status
- raw bandwidth
- filtered bandwidth
- raw min/max
- filtered min/max
- output image path

## Virtual Weigh Cell Simulator

Launch the standalone simulator with:

```bash
python3 weigh_cell_simulator.py
```

The simulator currently covers the requested weigh-cell features:

- scaling
- zero-scaling
- auto-scaling
- tare
- start machine / stop machine
- status blinker

## Build Targets

```bash
make triangular
make rectangular
make hamming
make hanning
make blackman
make kaiser
make parks_mcclellan
make frequency_sampling
make least_squares
make clean
```

## Output Naming

Each analyzer writes a file named like:

```text
filtered_<method>_<input_file>.txt
```

Example:

```text
filtered_hamming_535g20250502pm427ms20hz92.txt
```

The exporter writes plots like:

```text
plots/hamming/plot_hamming_535g20250502pm427ms20hz92.txt.png
```

## Notes

- The GUI uses dynamic axis scaling so filtered signals remain visible even when their range is smaller than the raw data.
- The exporter and GUI reuse the same loading logic from `main_plot_program.py`.
- Parks-McClellan is implemented as an IRLS-style approximation in the current C analyzer.

## Typical Workflow

```bash
make all
./new_run.sh
python save_all_plots.py
```

## License

No explicit license file is currently included.