// dsp_program.c: DSP analysis program to be called by the weigh client.
// It performs FIR filtering on a given data file and saves the results.

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

// Pre-calculated FIR coefficients
#define NUMTAPS 51
const float fir_coeffs[NUMTAPS] = {
    0.0003009503f, -0.0007802741f, -0.0018862922f, -0.002575211f, -0.0022712903f,
    0.0000000000f, 0.0034608358f, 0.008447385f, 0.013271783f, 0.016259074f,
    0.015949741f, 0.011409384f, 0.002347918f, -0.009774618f, -0.023533866f,
    -0.03713600f, -0.04859069f, -0.05609462f, -0.05814524f, -0.05389642f,
    -0.04396342f, -0.02927233f, -0.010996894f, 0.009149862f, 0.029676579f,
    0.04944807f, 0.06734796f, 0.08226068f, 0.09315512f, 0.09919539f,
    0.09919539f, 0.09315512f, 0.08226068f, 0.06734796f, 0.04944807f,
    0.029676579f, 0.009149862f, -0.010996894f, -0.02927233f, -0.04396342f,
    -0.05389642f, -0.05814524f, -0.05609462f, -0.04859069f, -0.03713600f,
    -0.023533866f, -0.009774618f, 0.002347918f, 0.011409384f, 0.015949741f,
    0.016259074f
};

// Calibration constants (example values)
const float ZERO_CAL = 0.01823035255075f;
const float SCALE_CAL = 0.00000451794631f;

// DSP Functions
int normalize_to_weights(const int* values, int num_values, float* weights_out) {
    if (!values || !weights_out || num_values <= 0) {
        fprintf(stderr, "[DSP] Error: Invalid input to normalize_to_weights.\n");
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

int fir_filter(const float* values, int num_values, float* filtered_values_out) {
    if (!values || !filtered_values_out || num_values <= 0) {
        fprintf(stderr, "[DSP] Error: Invalid input to fir_filter.\n");
        return -1;
    }

    if (num_values < NUMTAPS) {
        fprintf(stderr, "[DSP] Warning: Data length (%d) < NUMTAPS (%d). Skipping filter.\n", num_values, NUMTAPS);
        return 0;
    }

    arm_fir_instance_f32 S;
    float* state = (float*) calloc((size_t)(NUMTAPS + num_values - 1), sizeof(float));
    if (!state) {
        fprintf(stderr, "[DSP] Error: Memory allocation failed for FIR state buffer.\n");
        return -1;
    }

    arm_fir_init_f32(&S, NUMTAPS, (float*)fir_coeffs, state, num_values);
    arm_fir_f32(&S, (float*)values, filtered_values_out, num_values);
    free(state);
    return 0;
}

// Function to save processed data to a file
void save_data(const char* filepath, const float* data, int num_points) {
    FILE* fp = fopen(filepath, "w");
    if (fp) {
        for (int i = 0; i < num_points; ++i) {
            fprintf(fp, "%.6f\n", data[i]);
        }
        fclose(fp);
        printf("[DSP] Filtered data saved to: %s\n", filepath);
    } else {
        perror("[DSP] Failed to save filtered data");
    }
}


int main(int argc, char* argv[]) {
    if (argc < 2) {
        fprintf(stderr, "[DSP] Usage: %s <input_file.txt>\n", argv[0]);
        return 1;
    }

    const char* input_filepath = argv[1];
    printf("[DSP] Analyzing file: %s\n", input_filepath);

    FILE* f = fopen(input_filepath, "r");
    if (!f) {
        perror("[DSP] Failed to open input file");
        return 1;
    }

    char line[512];
    int current_adc_count = 0;
    int temp_adc_capacity = 256;
    int* temp_adc_values = (int*)malloc(sizeof(int) * temp_adc_capacity);
    if (!temp_adc_values) {
        perror("[DSP] Memory allocation failed");
        fclose(f);
        return 1;
    }

    while (fgets(line, sizeof(line), f)) {
        int adc_val;
        if (sscanf(line, "%d", &adc_val) == 1) {
            if (current_adc_count >= temp_adc_capacity) {
                temp_adc_capacity *= 2;
                int* new_temp = (int*)realloc(temp_adc_values, sizeof(int) * temp_adc_capacity);
                if (!new_temp) {
                    perror("[DSP] Reallocation failed");
                    free(temp_adc_values);
                    fclose(f);
                    return 1;
                }
                temp_adc_values = new_temp;
            }
            temp_adc_values[current_adc_count++] = adc_val;
        }
    }
    fclose(f);

    if (current_adc_count == 0) {
        fprintf(stderr, "[DSP] No valid ADC data found in the file.\n");
        free(temp_adc_values);
        return 1;
    }

    float* raw_weights = (float*)malloc(sizeof(float) * current_adc_count);
    float* filtered_weights = (float*)malloc(sizeof(float) * current_adc_count);

    if (!raw_weights || !filtered_weights) {
        perror("[DSP] Memory allocation for data arrays failed");
        free(temp_adc_values);
        if (raw_weights) free(raw_weights);
        if (filtered_weights) free(filtered_weights);
        return 1;
    }

    // Normalize ADC values
    normalize_to_weights(temp_adc_values, current_adc_count, raw_weights);

    // Apply FIR filter
    fir_filter(raw_weights, current_adc_count, filtered_weights);

    // Save filtered data
    char output_filepath[PATH_MAX];
    snprintf(output_filepath, sizeof(output_filepath), "filtered_%s", strrchr(input_filepath, '/') + 1);

    save_data(output_filepath, filtered_weights, current_adc_count);
    
    printf("[DSP] Analysis complete.\n");

    // Cleanup
    free(temp_adc_values);
    free(raw_weights);
    free(filtered_weights);

    return 0;
}
