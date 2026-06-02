#!/bin/bash

# Runs all windowing C analyzers for every input file, stores outputs in
# per-window folders, then launches the Python GUI plotter.

# --- Configuration ---
WORKING_DIR="/home/vishnu/Documents/CMS"
PYTHON_SCRIPT="main_plot_program.py"
WINDOWS=(triangular rectangular hamming hanning blackman kaiser parks_mcclellan frequency_sampling least_squares)

echo "Navigating to working directory: $WORKING_DIR"
cd "$WORKING_DIR" || { echo "Error: Could not change to $WORKING_DIR"; exit 1; }

echo "--- Step 1: Discover Input Files ---"
mapfile -t FILE_LIST < <(ls -1 adc_data/*.txt 2>/dev/null)
if [ ${#FILE_LIST[@]} -eq 0 ]; then
    echo "Error: No .txt files found in adc_data/."
    exit 1
fi

echo "Found ${#FILE_LIST[@]} input file(s) in adc_data/."

echo "--- Step 2: Build Missing Window Executables ---"
for win in "${WINDOWS[@]}"; do
    exe="./signal_analyzer_${win}"
    if [ ! -x "$exe" ]; then
        echo "Building missing executable: signal_analyzer_${win}"
        make "$win" || { echo "Error: Build failed for $win"; exit 1; }
    fi
done

echo "--- Step 3: Run All Windowing Methods For Every File ---"
for INPUT_FILE in "${FILE_LIST[@]}"; do
    BASE_FILENAME=$(basename "$INPUT_FILE")
    echo "Processing input file: $BASE_FILENAME"

    for win in "${WINDOWS[@]}"; do
        exe="./signal_analyzer_${win}"
        out_file="filtered_${win}_${BASE_FILENAME}"
        out_dir="output/${win}"
        mkdir -p "$out_dir"

        echo "Running $exe on $INPUT_FILE"
        "$exe" "$INPUT_FILE" || { echo "Error: ${exe} failed for ${BASE_FILENAME}"; exit 1; }

        if [ -f "$out_file" ]; then
            mv -f "$out_file" "$out_dir/"
            echo "Stored: $out_dir/$out_file"
        else
            echo "Error: Expected output file not found: $out_file"
            exit 1
        fi
    done
done

echo "--- Step 4: Launch Python Plot GUI ---"
if [ -d "venv" ]; then
    source venv/bin/activate || { echo "Error: Failed to activate venv"; exit 1; }
else
    echo "Error: venv not found in $WORKING_DIR"
    echo "Create it with: python3 -m venv venv && source venv/bin/activate && pip install matplotlib numpy"
    exit 1
fi

echo "Launching plot GUI with file dropdown for all processed inputs"
python "$PYTHON_SCRIPT"

deactivate
echo "--- Automation Script Finished Successfully ---"
