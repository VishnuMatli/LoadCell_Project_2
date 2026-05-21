// signal_analyzer_kaiser.c: DSP analysis with KAISER WINDOW applied to FIR coefficients
// Window Type: KAISER - Adjustable sidelobe control via beta parameter
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
#define KAISER_BETA 5.0f

// Calibration constants
const float ZERO_CAL = 0.01823035255075f;
const float SCALE_CAL = 0.00000451794631f;

static float bessel_i0(float x) {
    float sum = 1.0f;
    float term = 1.0f;
    float half_x = x * 0.5f;
    for (int k = 1; k <= 20; ++k) {
        term *= (half_x * half_x) / ((float)k * (float)k);
        sum += term;
        if (term < 1e-8f) {
            break;
        }
    }
    return sum;
}

// Generate FIR coefficients with KAISER window
void generate_fir_coeffs_kaiser(float* coeffs, int num_taps,
                                float cutoff_freq, float sampling_freq) {
    float fc = cutoff_freq / sampling_freq;
    float alpha = (num_taps - 1) / 2.0f;
    float gain = 0.0f;
    float denom = bessel_i0(KAISER_BETA);

    printf("[DSP_KAISER] Generating FIR coefficients with KAISER window\n");
    printf("[DSP_KAISER] Cutoff: %.2f Hz, Sampling: %.2f Hz, Normalized fc: %.4f\n",
           cutoff_freq, sampling_freq, fc);

    for (int n = 0; n < num_taps; n++) {
        float sinc_val;
        if (fabsf((float)n - alpha) < 1e-9f) {
            sinc_val = 2.0f * fc;
        } else {
            sinc_val = arm_sin_f32(2.0f * PI * fc * ((float)n - alpha)) /
                       (PI * ((float)n - alpha));
        }

        float ratio = ((float)n - alpha) / alpha;
        float inside = 1.0f - ratio * ratio;
        if (inside < 0.0f) {
            inside = 0.0f;
        }
        float kaiser_window = bessel_i0(KAISER_BETA * sqrtf(inside)) / denom;

        coeffs[n] = sinc_val * kaiser_window;
        gain += coeffs[n];
    }

    for (int n = 0; n < num_taps; n++) {
        coeffs[n] /= gain;
    }

    printf("[DSP_KAISER] FIR coefficients generated and normalized\n");
}

int normalize_to_weights(const int* values, int num_values, float* weights_out) {
    if (!values || !weights_out || num_values <= 0) {
        fprintf(stderr, "[DSP_KAISER] Error: Invalid input to normalize_to_weights.\n");
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
        fprintf(stderr, "[DSP_KAISER] Error: Invalid input to fir_filter.\n");
        return -1;
    }

    if (num_values < NUMTAPS) {
        fprintf(stderr, "[DSP_KAISER] Warning: Data length (%d) < NUMTAPS (%d). Skipping filter.\n",
                num_values, NUMTAPS);
        return 0;
    }

    arm_fir_instance_f32 S;
    float* state = (float*)calloc((size_t)(NUMTAPS + num_values - 1), sizeof(float));
    if (!state) {
        fprintf(stderr, "[DSP_KAISER] Error: Memory allocation failed for FIR state buffer.\n");
        return -1;
    }

    arm_fir_init_f32(&S, NUMTAPS, (float*)fir_coeffs, state, num_values);
    for (int i = 0; i < NUMTAPS - 1; ++i) {
        state[i] = values[0];
    }
    arm_fir_f32(&S, (float*)values, filtered_values_out, num_values);

    free(state);
    printf("[DSP_KAISER] FIR filtering completed\n");
    return 0;
}

void save_data(const char* filepath, const float* data, int num_points) {
    FILE* fp = fopen(filepath, "w");
    if (fp) {
        for (int i = 0; i < num_points; ++i) {
            fprintf(fp, "%.6f\n", data[i]);
        }
        fclose(fp);
        printf("[DSP_KAISER] Filtered data saved to: %s\n", filepath);
    } else {
        perror("[DSP_KAISER] Failed to save filtered data");
    }
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "[DSP_KAISER] Usage: %s <input_file.txt>\n", argv[0]);
        fprintf(stderr, "[DSP_KAISER] Method: KAISER\n");
        fprintf(stderr, "[DSP_KAISER] Cutoff Frequency: %.2f Hz\n", CUTOFF_FREQ);
        return 1;
    }

    const char* input_filepath = argv[1];
    printf("[DSP_KAISER] ========================================\n");
    printf("[DSP_KAISER] Analyzing file: %s\n", input_filepath);
    printf("[DSP_KAISER] Method: KAISER\n");
    printf("[DSP_KAISER] Cutoff Frequency: %.2f Hz\n", CUTOFF_FREQ);
    printf("[DSP_KAISER] ========================================\n");

    FILE* f = fopen(input_filepath, "r");
    if (!f) {
        perror("[DSP_KAISER] Failed to open input file");
        return 1;
    }

    char line[512];
    int current_adc_count = 0;
    int temp_adc_capacity = 256;
    int* temp_adc_values = (int*)malloc(sizeof(int) * temp_adc_capacity);
    if (!temp_adc_values) {
        perror("[DSP_KAISER] Memory allocation failed");
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
                perror("[DSP_KAISER] Reallocation failed");
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
        fprintf(stderr, "[DSP_KAISER] No valid ADC data found in the file.\n");
        free(temp_adc_values);
        return 1;
    }

    printf("[DSP_KAISER] Read %d ADC samples from file\n", current_adc_count);

    float* raw_weights = (float*)malloc(sizeof(float) * current_adc_count);
    float* filtered_weights = (float*)malloc(sizeof(float) * current_adc_count);
    float* fir_coeffs = (float*)malloc(sizeof(float) * NUMTAPS);

    if (!raw_weights || !filtered_weights || !fir_coeffs) {
        perror("[DSP_KAISER] Memory allocation for data arrays failed");
        free(temp_adc_values);
        if (raw_weights) free(raw_weights);
        if (filtered_weights) free(filtered_weights);
        if (fir_coeffs) free(fir_coeffs);
        return 1;
    }

    generate_fir_coeffs_kaiser(fir_coeffs, NUMTAPS, CUTOFF_FREQ, SAMPLING_FREQ);
    normalize_to_weights(temp_adc_values, current_adc_count, raw_weights);
    printf("[DSP_KAISER] Normalized ADC values to weights\n");

    fir_filter(raw_weights, current_adc_count, filtered_weights, fir_coeffs);

    char output_filepath[PATH_MAX];
    snprintf(output_filepath, sizeof(output_filepath), "filtered_kaiser_%s",
             strrchr(input_filepath, '/') ? strrchr(input_filepath, '/') + 1 : input_filepath);

    save_data(output_filepath, filtered_weights, current_adc_count);

    printf("[DSP_KAISER] ========================================\n");
    printf("[DSP_KAISER] Analysis complete!\n");
    printf("[DSP_KAISER] ========================================\n");

    free(temp_adc_values);
    free(raw_weights);
    free(filtered_weights);
    free(fir_coeffs);

    return 0;
}
