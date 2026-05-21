#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "arm_math.h"   // CMSIS-DSP

#define BLOCK_SIZE 1
#define NUM_TAPS_01 64
#define FFT_SIZE 256
#define ENERGY_THRESHOLD 0.9f
//#define PI 3.14159265358979323846f

// FIR filter state
static arm_fir_instance_f32 S01;
static float32_t firStateF32_01[NUM_TAPS_01 + BLOCK_SIZE - 1];
static float32_t firCoeffs_dyn_01[NUM_TAPS_01];
static float32_t sample_buffer_01[FFT_SIZE];
static uint32_t sample_count_01 = 0;
static float32_t fs = 1000.0f; // Sampling rate (adjust if needed)

// FFT
static arm_rfft_fast_instance_f32 rfft_instance;
static float32_t fft_output[FFT_SIZE];

// --- DSP helpers ---
float32_t find_cutoff_from_signal(float32_t *signal_block, float32_t sample_freq) {
    arm_rfft_fast_f32(&rfft_instance, signal_block, fft_output, 0);
    float32_t magnitudes[FFT_SIZE/2];
    arm_cmplx_mag_f32(fft_output, magnitudes, FFT_SIZE/2);

    float32_t total_energy = 0.0f;
    for (int i=0;i<FFT_SIZE/2;i++) total_energy += magnitudes[i]*magnitudes[i];
    if (total_energy < 1e-9) return 20.0f;

    float32_t cumulative = 0.0f;
    for (int i=0;i<FFT_SIZE/2;i++) {
        cumulative += magnitudes[i]*magnitudes[i];
        if (cumulative >= total_energy * ENERGY_THRESHOLD) {
            return (i) * (sample_freq / (float32_t)FFT_SIZE);
        }
    }
    return (FFT_SIZE/2) * (sample_freq / (float32_t)FFT_SIZE);
}

void generate_low_pass_fir_coeffs(float32_t *coeffs, uint16_t num_taps, float32_t cutoff_freq, float32_t sample_freq) {
    float32_t fc = cutoff_freq / sample_freq;
    float32_t alpha = (num_taps - 1) / 2.0f;

    for (uint16_t n=0;n<num_taps;n++) {
        float32_t sinc_val;
        if (fabsf(n - alpha) < 1e-6) {
            sinc_val = 2.0f * fc;
        } else {
            sinc_val = arm_sin_f32(2.0f * PI * fc * (n - alpha)) / (PI * (n - alpha));
        }

        // Hamming window
        float32_t window = 0.54f - 0.46f * arm_cos_f32(2.0f * PI * n / (num_taps-1));
        coeffs[n] = sinc_val * window;
    }

    // Normalize coefficients
    float32_t sum = 0.0f;
    for (uint16_t n=0;n<num_taps;n++) {
        sum += coeffs[n];
    }
    for (uint16_t n=0;n<num_taps;n++) {
        coeffs[n] /= sum;
    }
}

// --- initialize filter ---
void init_dfilter2_01(void) {
    // Start with a fixed cutoff so outputs are not zero in the beginning
    generate_low_pass_fir_coeffs(firCoeffs_dyn_01, NUM_TAPS_01, 50.0f, fs);
    arm_fir_init_f32(&S01, NUM_TAPS_01, firCoeffs_dyn_01, firStateF32_01, BLOCK_SIZE);
    arm_rfft_fast_init_f32(&rfft_instance, FFT_SIZE);
}

// --- filtering ---
float dfilter2_01(float input) {
    if (sample_count_01 < FFT_SIZE) {
        sample_buffer_01[sample_count_01++] = input;
    } else {
        memmove(&sample_buffer_01[0], &sample_buffer_01[1], (FFT_SIZE-1)*sizeof(float32_t));
        sample_buffer_01[FFT_SIZE-1] = input;
    }

    // Update FIR dynamically once enough samples collected
    if (sample_count_01 >= FFT_SIZE && (sample_count_01 % (FFT_SIZE/2)) == 0) {
        float32_t cutoff = find_cutoff_from_signal(sample_buffer_01, fs);
        generate_low_pass_fir_coeffs(firCoeffs_dyn_01, NUM_TAPS_01, cutoff, fs);
        arm_fir_init_f32(&S01, NUM_TAPS_01, firCoeffs_dyn_01, firStateF32_01, BLOCK_SIZE);
    }

    float32_t input_val = input;
    float32_t output_val = 0.0f;
    arm_fir_f32(&S01, &input_val, &output_val, BLOCK_SIZE);
    return output_val;
}

// --- main program ---
int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s inputfile.txt\n", argv[0]);
        return 1;
    }

    char *infile = argv[1];
    char outfile[512];
    snprintf(outfile, sizeof(outfile), "output/filtered_%s", strrchr(infile,'/') ? strrchr(infile,'/')+1 : infile);

    FILE *fin = fopen(infile, "r");
    if (!fin) {
        perror("Error opening input file");
        return 1;
    }

    FILE *fout = fopen(outfile, "w");
    if (!fout) {
        perror("Error opening output file");
        fclose(fin);
        return 1;
    }

    init_dfilter2_01();

    float val;
    int line = 0;
    //while(fscanf(fin, "ADC:%f", &val) == 1) {
    while (fscanf(fin, "%f", &val) == 1) {
        float out = dfilter2_01(val);
        fprintf(fout, "%f\n", out);

        // Debug print first 10 samples
        if (line < 10) {
            printf("DEBUG: in=%f -> out=%f\n", val, out);
        }
        line++;
    }

    fclose(fin);
    fclose(fout);

    printf("Processed %d samples. Filtered data written to %s\n", line, outfile);
    return 0;
}