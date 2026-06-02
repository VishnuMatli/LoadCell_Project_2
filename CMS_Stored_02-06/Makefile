# Makefile for CMS DSP Signal Analyzer with Multiple Windowing Methods
# Compiles all window function variants
# Usage: make all
#        make triangular
#        make rectangular
#        make hamming
#        make hanning
#        make blackman
#        make kaiser
#        make parks_mcclellan
#        make frequency_sampling
#        make least_squares
#        make clean

CC = gcc
CFLAGS = -I./CMSIS-DSP/Include -I./CMSIS_5/CMSIS/Core/Include
LDLIBS = -lm -pthread
LDFLAGS = -L./CMSIS-DSP/Source

# CMSIS-DSP source files (commonly used in all variants)
CMSIS_SOURCES = \
	./CMSIS-DSP/Source/FilteringFunctions/arm_fir_f32.c \
	./CMSIS-DSP/Source/FilteringFunctions/arm_fir_init_f32.c \
	./CMSIS-DSP/Source/FastMathFunctions/arm_sin_f32.c \
	./CMSIS-DSP/Source/FastMathFunctions/arm_cos_f32.c \
	./CMSIS-DSP/Source/CommonTables/arm_common_tables.c

# Executables
EXEC_TRIANGULAR = signal_analyzer_triangular
EXEC_RECTANGULAR = signal_analyzer_rectangular
EXEC_HAMMING = signal_analyzer_hamming
EXEC_HANNING = signal_analyzer_hanning
EXEC_BLACKMAN = signal_analyzer_blackman
EXEC_KAISER = signal_analyzer_kaiser
EXEC_PARKS_MCCLELLAN = signal_analyzer_parks_mcclellan
EXEC_FREQUENCY_SAMPLING = signal_analyzer_frequency_sampling
EXEC_LEAST_SQUARES = signal_analyzer_least_squares

# All executables
ALL_EXEC = $(EXEC_TRIANGULAR) $(EXEC_RECTANGULAR) $(EXEC_HAMMING) $(EXEC_HANNING) $(EXEC_BLACKMAN) $(EXEC_KAISER) $(EXEC_PARKS_MCCLELLAN) $(EXEC_FREQUENCY_SAMPLING) $(EXEC_LEAST_SQUARES)

.PHONY: all triangular rectangular hamming hanning blackman kaiser parks_mcclellan frequency_sampling least_squares clean help

help:
	@echo "==================================================================="
	@echo "CMS DSP Signal Analyzer - Windowing Methods Makefile"
	@echo "==================================================================="
	@echo "Available targets:"
	@echo "  make all           - Compile all windowing variants"
	@echo "  make triangular    - Compile triangular window version"
	@echo "  make rectangular   - Compile rectangular window version"
	@echo "  make hamming       - Compile hamming window version"
	@echo "  make hanning       - Compile hanning window version"
	@echo "  make blackman      - Compile blackman window version"
	@echo "  make kaiser        - Compile Kaiser window version"
	@echo "  make parks_mcclellan - Compile Parks-McClellan version"
	@echo "  make frequency_sampling - Compile frequency sampling version"
	@echo "  make least_squares - Compile least-squares version"
	@echo "  make clean         - Remove all compiled executables"
	@echo "  make help          - Show this help message"
	@echo "==================================================================="
	@echo "Usage example:"
	@echo "  ./signal_analyzer_triangular adc_data/sample_file.txt"
	@echo "==================================================================="

all: $(ALL_EXEC)
	@echo "==================================================================="
	@echo "✓ All windowing variants compiled successfully!"
	@echo "==================================================================="
	@echo "Compiled executables:"
	@echo "  - $(EXEC_TRIANGULAR)"
	@echo "  - $(EXEC_RECTANGULAR)"
	@echo "  - $(EXEC_HAMMING)"
	@echo "  - $(EXEC_HANNING)"
	@echo "  - $(EXEC_BLACKMAN)"
	@echo "  - $(EXEC_KAISER)"
	@echo "  - $(EXEC_PARKS_MCCLELLAN)"
	@echo "  - $(EXEC_FREQUENCY_SAMPLING)"
	@echo "  - $(EXEC_LEAST_SQUARES)"
	@echo "==================================================================="

# Triangular window
$(EXEC_TRIANGULAR): signal_analyzer_triangular.c $(CMSIS_SOURCES)
	@echo "[Compiling] TRIANGULAR window variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_triangular.c -o $(EXEC_TRIANGULAR) $(LDLIBS)
	@echo "✓ $(EXEC_TRIANGULAR) created"

# Rectangular window
$(EXEC_RECTANGULAR): signal_analyzer_rectangular.c $(CMSIS_SOURCES)
	@echo "[Compiling] RECTANGULAR window variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_rectangular.c -o $(EXEC_RECTANGULAR) $(LDLIBS)
	@echo "✓ $(EXEC_RECTANGULAR) created"

# Hamming window
$(EXEC_HAMMING): signal_analyzer_hamming.c $(CMSIS_SOURCES)
	@echo "[Compiling] HAMMING window variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_hamming.c -o $(EXEC_HAMMING) $(LDLIBS)
	@echo "✓ $(EXEC_HAMMING) created"

# Hanning window
$(EXEC_HANNING): signal_analyzer_hanning.c $(CMSIS_SOURCES)
	@echo "[Compiling] HANNING window variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_hanning.c -o $(EXEC_HANNING) $(LDLIBS)
	@echo "✓ $(EXEC_HANNING) created"

# Blackman window
$(EXEC_BLACKMAN): signal_analyzer_blackman.c $(CMSIS_SOURCES)
	@echo "[Compiling] BLACKMAN window variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_blackman.c -o $(EXEC_BLACKMAN) $(LDLIBS)
	@echo "✓ $(EXEC_BLACKMAN) created"

# Kaiser window
$(EXEC_KAISER): signal_analyzer_kaiser.c $(CMSIS_SOURCES)
	@echo "[Compiling] KAISER method variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_kaiser.c -o $(EXEC_KAISER) $(LDLIBS)
	@echo "✓ $(EXEC_KAISER) created"

# Parks-McClellan
$(EXEC_PARKS_MCCLELLAN): signal_analyzer_parks_mcclellan.c $(CMSIS_SOURCES)
	@echo "[Compiling] PARKS-MCCLELLAN method variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_parks_mcclellan.c -o $(EXEC_PARKS_MCCLELLAN) $(LDLIBS)
	@echo "✓ $(EXEC_PARKS_MCCLELLAN) created"

# Frequency Sampling
$(EXEC_FREQUENCY_SAMPLING): signal_analyzer_frequency_sampling.c $(CMSIS_SOURCES)
	@echo "[Compiling] FREQUENCY SAMPLING method variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_frequency_sampling.c -o $(EXEC_FREQUENCY_SAMPLING) $(LDLIBS)
	@echo "✓ $(EXEC_FREQUENCY_SAMPLING) created"

# Least Squares
$(EXEC_LEAST_SQUARES): signal_analyzer_least_squares.c $(CMSIS_SOURCES)
	@echo "[Compiling] LEAST SQUARES method variant..."
	$(CC) $(CFLAGS) $(CMSIS_SOURCES) signal_analyzer_least_squares.c -o $(EXEC_LEAST_SQUARES) $(LDLIBS)
	@echo "✓ $(EXEC_LEAST_SQUARES) created"

# Individual targets
triangular: $(EXEC_TRIANGULAR)
rectangular: $(EXEC_RECTANGULAR)
hamming: $(EXEC_HAMMING)
hanning: $(EXEC_HANNING)
blackman: $(EXEC_BLACKMAN)
kaiser: $(EXEC_KAISER)
parks_mcclellan: $(EXEC_PARKS_MCCLELLAN)
frequency_sampling: $(EXEC_FREQUENCY_SAMPLING)
least_squares: $(EXEC_LEAST_SQUARES)

# Clean up
clean:
	@echo "[Cleaning] Removing all compiled executables..."
	@rm -f $(ALL_EXEC)
	@echo "✓ Cleanup complete"

print-%:
	@echo $* = $($*)
