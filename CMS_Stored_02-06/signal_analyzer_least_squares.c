// signal_analyzer_least_squares.c: DSP analysis using Least Squares FIR design
// Method: LEAST SQUARES - FIR coefficients from weighted LS fitting
// Uses CMSIS-DSP library for FIR filtering

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/stat.h>
#include <stdint.h>
#include <limits.h>
#include <errno.h>

// Include the necessary CMSIS-DSP headers
#include "arm_math.h"
#include "arm_const_structs.h"

// FIR Filter Configuration
#define NUMTAPS 11
#ifndef PI
#define PI 3.14159265358979323846f
#endif
#define CUTOFF_FREQ 10.0f      // Cutoff frequency in Hz
#define SAMPLING_FREQ 50.0f    // Sampling frequency in Hz
#define GRID_POINTS 256

// Calibration constants
const float ZERO_CAL = 0.01823035255075f;
const float SCALE_CAL = 0.00000451794631f;

static int solve_linear_system(float* A, float* b, float* x, int n) {
    for (int i = 0; i < n; ++i) {
        int pivot = i;
        float max_val = fabsf(A[i * n + i]);
        for (int r = i + 1; r < n; ++r) {
            float v = fabsf(A[r * n + i]);
            if (v > max_val) {
                max_val = v;
                pivot = r;
            }
        }
        if (max_val < 1e-8f) {
            return -1;
        }
        if (pivot != i) {
            for (int c = 0; c < n; ++c) {
                float tmp = A[i * n + c];
                A[i * n + c] = A[pivot * n + c];
                A[pivot * n + c] = tmp;
            }
            float tb = b[i];
            b[i] = b[pivot];
            b[pivot] = tb;
        }

        float diag = A[i * n + i];
        for (int c = i; c < n; ++c) {
            A[i * n + c] /= diag;
        }
        b[i] /= diag;

        for (int r = 0; r < n; ++r) {
            if (r == i) {
                continue;
            }
            float factor = A[r * n + i];
            for (int c = i; c < n; ++c) {
                A[r * n + c] -= factor * A[i * n + c];
            }
            b[r] -= factor * b[i];
        }
    }

    for (int i = 0; i < n; ++i) {
        x[i] = b[i];
    }
    return 0;
}

// Generate FIR coefficients using Least Squares Method
void generate_fir_coeffs_least_squares(float* coeffs, int num_taps,
                                       float cutoff_freq, float sampling_freq) {
    float fc = cutoff_freq / sampling_freq;
    int M = (num_taps - 1) / 2;
    int unknowns = M + 1;
    float ATA[64] = {0.0f};
    float ATd[8] = {0.0f};
    float a[8] = {0.0f};

    printf("[DSP_LEASTSQ] Generating FIR coefficients with LEAST SQUARES method\n");
    printf("[DSP_LEASTSQ] Cutoff: %.2f Hz, Sampling: %.2f Hz, Normalized fc: %.4f\n",
           cutoff_freq, sampling_freq, fc);

    for (int i = 0; i < GRID_POINTS; ++i) {
        float w = PI * (float)i / (float)(GRID_POINTS - 1);
        float f_norm = w / (2.0f * PI);
        float desired = (f_norm <= fc) ? 1.0f : 0.0f;
        float weight = (f_norm <= fc) ? 1.0f : 1.5f;

        float phi[8] = {0.0f};
        phi[0] = 1.0f;
        for (int k = 1; k <= M; ++k) {
            phi[k] = 2.0f * cosf((float)k * w);
        }

        for (int r = 0; r < unknowns; ++r) {
            ATd[r] += weight * phi[r] * desired;
            for (int c = 0; c < unknowns; ++c) {
                ATA[r * unknowns + c] += weight * phi[r] * phi[c];
            }
        }
    }

    if (solve_linear_system(ATA, ATd, a, unknowns) != 0) {
        fprintf(stderr, "[DSP_LEASTSQ] Warning: LS solve failed, falling back to sinc design.\n");
        float alpha = (num_taps - 1) / 2.0f;
        float gain = 0.0f;
        for (int n = 0; n < num_taps; ++n) {
            if (fabsf((float)n - alpha) < 1e-9f) {
                coeffs[n] = 2.0f * fc;
            } else {
                coeffs[n] = arm_sin_f32(2.0f * PI * fc * ((float)n - alpha)) /
                            (PI * ((float)n - alpha));
            }
            gain += coeffs[n];
        }
        for (int n = 0; n < num_taps; ++n) {
            coeffs[n] /= gain;
        }
    } else {
        coeffs[M] = a[0];
        for (int k = 1; k <= M; ++k) {
            coeffs[M + k] = a[k];
            coeffs[M - k] = a[k];
        }

        float gain = 0.0f;
        for (int n = 0; n < num_taps; ++n) {
            gain += coeffs[n];
        }
        for (int n = 0; n < num_taps; ++n) {
            coeffs[n] /= gain;
        }
    }

    printf("[DSP_LEASTSQ] FIR coefficients generated and normalized\n");
}

int normalize_to_weights(const int* values, int num_values, float* weights_out) {
    if (!values || !weights_out || num_values <= 0) {
        fprintf(stderr, "[DSP_LEASTSQ] Error: Invalid input to normalize_to_weights.\n");
        return -1;
    }
    const float ADC_MAX_VAL_FLOAT = 2147483648.0f;
    for (int i = 0; i < num_values; ++i) {
        float data_in = (float)values[i] / ADC_MAX_VAL_FLOAT;
        if (SCALE_CAL != 0.0f) {
            weights_out[i] = (data_in - ZERO_CAL) / SCALE_CAL;
        } else {
            weights_out[i] = 0.0f;
        }
    }
    return 0;
}

int fir_filter(const float* values, int num_values, float* filtered_values_out,
               const float* fir_coeffs) {
    if (!values || !filtered_values_out || !fir_coeffs || num_values <= 0) {
        fprintf(stderr, "[DSP_LEASTSQ] Error: Invalid input to fir_filter.\n");
        return -1;
    }

    if (num_values < NUMTAPS) {
        fprintf(stderr, "[DSP_LEASTSQ] Warning: Data length (%d) < NUMTAPS (%d). Skipping filter.\n",
                num_values, NUMTAPS);
        return 0;
    }

    arm_fir_instance_f32 S;
    float* state = (float*)calloc((size_t)(NUMTAPS + num_values - 1), sizeof(float));
    if (!state) {
        fprintf(stderr, "[DSP_LEASTSQ] Error: Memory allocation failed for FIR state buffer.\n");
        return -1;
    }

    arm_fir_init_f32(&S, NUMTAPS, (float*)fir_coeffs, state, num_values);
    for (int i = 0; i < NUMTAPS - 1; ++i) {
        state[i] = values[0];
    }
    arm_fir_f32(&S, (float*)values, filtered_values_out, num_values);

    free(state);
    printf("[DSP_LEASTSQ] FIR filtering completed\n");
    return 0;
}

void save_data(const char* filepath, const float* data, int num_points) {
    FILE* fp = fopen(filepath, "w");
    if (fp) {
        for (int i = 0; i < num_points; ++i) {
            fprintf(fp, "%.6f\n", data[i]);
        }
        fclose(fp);
        printf("[DSP_LEASTSQ] Filtered data saved to: %s\n", filepath);
    } else {
        perror("[DSP_LEASTSQ] Failed to save filtered data");
    }
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "[DSP_LEASTSQ] Usage: %s <input_file.txt>\n", argv[0]);
        fprintf(stderr, "[DSP_LEASTSQ] Method: LEAST SQUARES\n");
        fprintf(stderr, "[DSP_LEASTSQ] Cutoff Frequency: %.2f Hz\n", CUTOFF_FREQ);
        return 1;
    }

    const char* input_filepath = argv[1];
    printf("[DSP_LEASTSQ] ========================================\n");
    printf("[DSP_LEASTSQ] Analyzing file: %s\n", input_filepath);
    printf("[DSP_LEASTSQ] Method: LEAST SQUARES\n");
    printf("[DSP_LEASTSQ] Cutoff Frequency: %.2f Hz\n", CUTOFF_FREQ);
    printf("[DSP_LEASTSQ] ========================================\n");

    FILE* f = fopen(input_filepath, "r");
    if (!f) {
        perror("[DSP_LEASTSQ] Failed to open input file");
        return 1;
    }

    char line[512];
    int current_adc_count = 0;
    int temp_adc_capacity = 256;
    int* temp_adc_values = (int*)malloc(sizeof(int) * temp_adc_capacity);
    if (!temp_adc_values) {
        perror("[DSP_LEASTSQ] Memory allocation failed");
        fclose(f);
        return 1;
    }

    while (fgets(line, sizeof(line), f)) {
        char* p = line;
        while (*p && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) p++;
        while (*p && (*p < '0' || *p > '9') && *p != '-') p++;
        if (!*p) continue;
        char* endptr = NULL;
        long val = strtol(p, &endptr, 10);
        if (p == endptr) continue;

        if (current_adc_count >= temp_adc_capacity) {
            temp_adc_capacity *= 2;
            int* new_temp = (int*)realloc(temp_adc_values, sizeof(int) * temp_adc_capacity);
            if (!new_temp) {
                perror("[DSP_LEASTSQ] Reallocation failed");
                free(temp_adc_values);
                fclose(f);
                return 1;
            }
            temp_adc_values = new_temp;
        }
        temp_adc_values[current_adc_count++] = (int)val;
    }
    fclose(f);

    if (current_adc_count == 0) {
        fprintf(stderr, "[DSP_LEASTSQ] No valid ADC data found in the file.\n");
        free(temp_adc_values);
        return 1;
    }

    printf("[DSP_LEASTSQ] Read %d ADC samples from file\n", current_adc_count);

    float* raw_weights = (float*)malloc(sizeof(float) * current_adc_count);
    float* filtered_weights = (float*)malloc(sizeof(float) * current_adc_count);
    float* fir_coeffs = (float*)malloc(sizeof(float) * NUMTAPS);

    if (!raw_weights || !filtered_weights || !fir_coeffs) {
        perror("[DSP_LEASTSQ] Memory allocation for data arrays failed");
        free(temp_adc_values);
        if (raw_weights) free(raw_weights);
        if (filtered_weights) free(filtered_weights);
        if (fir_coeffs) free(fir_coeffs);
        return 1;
    }

    generate_fir_coeffs_least_squares(fir_coeffs, NUMTAPS, CUTOFF_FREQ, SAMPLING_FREQ);
    normalize_to_weights(temp_adc_values, current_adc_count, raw_weights);
    printf("[DSP_LEASTSQ] Normalized ADC values to weights\n");

    fir_filter(raw_weights, current_adc_count, filtered_weights, fir_coeffs);

    char output_filepath[PATH_MAX];
    snprintf(output_filepath, sizeof(output_filepath), "filtered_least_squares_%s",
             strrchr(input_filepath, '/') ? strrchr(input_filepath, '/') + 1 : input_filepath);

    save_data(output_filepath, filtered_weights, current_adc_count);

    printf("[DSP_LEASTSQ] ========================================\n");
    printf("[DSP_LEASTSQ] Analysis complete!\n");
    printf("[DSP_LEASTSQ] ========================================\n");

    free(temp_adc_values);
    free(raw_weights);
    free(filtered_weights);
    free(fir_coeffs);

    return 0;
}
