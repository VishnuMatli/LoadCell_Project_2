#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "arm_math.h"   // CMSIS-DSP

#define BLOCK_SIZE 1
#define NUM_TAPS 64
#define FFT_SIZE 256
#define ENERGY_THRESHOLD 0.9f

// FIR filter state
static arm_fir_instance_f32 S;
static float32_t firStateF32[NUM_TAPS + BLOCK_SIZE - 1];
static float32_t firCoeffs[NUM_TAPS];
static float32_t sample_buffer[FFT_SIZE];
static uint32_t sample_count = 0;
static float32_t fs = 1000.0f; // Sampling rate (adjust if needed)
static int filter_initialized = 0;

// FFT
static arm_rfft_fast_instance_f32 rfft_instance;
static float32_t fft_output[FFT_SIZE];
static float32_t fft_input[FFT_SIZE];


// --- DSP helpers ---
float32_t find_cutoff_from_signal(float32_t *signal_block, float32_t sample_freq) {
    // Copy to input buffer for FFT (rfft modifies the input buffer)
    arm_copy_f32(signal_block, fft_input, FFT_SIZE);
    arm_rfft_fast_f32(&rfft_instance, fft_input, fft_output, 0);
    float32_t magnitudes[FFT_SIZE/2];
    arm_cmplx_mag_f32(fft_output, magnitudes, FFT_SIZE/2);

    float32_t total_energy = 0.0f;
    for (int i=0;i<FFT_SIZE/2;i++) total_energy += magnitudes[i]*magnitudes[i];
    if (total_energy < 1e-9) return 20.0f; // Default cutoff if signal is silent

    float32_t cumulative = 0.0f;
    for (int i=0;i<FFT_SIZE/2;i++) {
        cumulative += magnitudes[i]*magnitudes[i];
        if (cumulative >= total_energy * ENERGY_THRESHOLD) {
            // Return the frequency of the bin where the energy threshold is crossed
            return (i+1) * (sample_freq / (float32_t)FFT_SIZE);
        }
    }
    // Fallback to Nyquist frequency if something goes wrong
    return (FFT_SIZE/2) * (sample_freq / (float32_t)FFT_SIZE);
}

void generate_low_pass_fir_coeffs(float32_t *coeffs, uint16_t num_taps, float32_t cutoff_freq, float32_t sample_freq) {
    float32_t fc = cutoff_freq / sample_freq;
    float32_t alpha = (num_taps - 1) / 2.0f;
    float32_t gain = 0.0f;

    for (uint16_t n=0;n<num_taps;n++) {
        float32_t sinc_val;
        if (fabsf(n - alpha) < 1e-9) {
            sinc_val = 2.0f * fc;
        } else {
            sinc_val = arm_sin_f32(2.0f * PI * fc * (n - alpha)) / (PI * (n - alpha));
        }
        float32_t window = 0.54f - 0.46f * arm_cos_f32(2.0f * PI * n / (num_taps-1)); // Hamming window
        coeffs[n] = sinc_val * window;
        gain += coeffs[n];
    }

    // Normalize coefficients for unity gain at DC
    for (uint16_t n=0;n<num_taps;n++) {
        coeffs[n] /= gain;
    }
}

// --- initialize filter ---
void init_filter_processing(void) {
    arm_rfft_fast_init_f32(&rfft_instance, FFT_SIZE);
    // Initialize FIR with dummy coefficients. It will be re-initialized later.
    // This prevents issues if dfilter is called before the buffer is full.
    for(int i=0; i<NUM_TAPS; i++) firCoeffs[i] = 0.0f;
    firCoeffs[0] = 1.0f;
    arm_fir_init_f32(&S, NUM_TAPS, firCoeffs, firStateF32, BLOCK_SIZE);
}


// --- filtering ---
float dfilter(float input) {
    if (!filter_initialized) {
        if (sample_count < FFT_SIZE) {
            sample_buffer[sample_count++] = input;
        }

        if (sample_count >= FFT_SIZE) {
            // Buffer is full, now we can determine the cutoff and init the real filter
            float32_t cutoff = find_cutoff_from_signal(sample_buffer, fs);
            printf("Determined cutoff frequency: %f Hz\n", cutoff);

            generate_low_pass_fir_coeffs(firCoeffs, NUM_TAPS, cutoff, fs);

            // Initialize the FIR filter instance with the new coefficients
            arm_fir_init_f32(&S, NUM_TAPS, firCoeffs, firStateF32, BLOCK_SIZE);

            filter_initialized = 1; // Mark filter as initialized
            
            // Now, filter the samples that we have in the buffer
            for(int i=0; i < FFT_SIZE; i++) {
                float32_t output_val = 0.0f;
                float32_t input_val = sample_buffer[i];
                arm_fir_f32(&S, &input_val, &output_val, BLOCK_SIZE);
                sample_buffer[i] = output_val; // Store filtered version
            }
            // Return the last filtered sample from the buffer
            return sample_buffer[FFT_SIZE-1];
        }
        // Before the filter is initialized, we can return 0 or the input
        return 0.0f;
    }

    // Once initialized, just filter the stream of incoming samples
    float32_t input_val = input;
    float32_t output_val = 0.0f;
    arm_fir_f32(&S, &input_val, &output_val, BLOCK_SIZE);
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
    snprintf(outfile, sizeof(outfile), "output/filtered_%s",
         strrchr(infile, '/') ? strrchr(infile, '/') + 1 : infile);


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

    init_filter_processing();

    float val;
    int count = 0;
    while (fscanf(fin, "%f", &val) == 1) {
        float out = dfilter(val);
        // After the initial buffer is filled and filtered, we start writing output
        if (filter_initialized && count >= FFT_SIZE) {
            fprintf(fout, "%f\n", out);
        } else if (filter_initialized) {
            // Write the already filtered buffer content
            fprintf(fout, "%f\n", sample_buffer[count]);
        }
        count++;
    }

    fclose(fin);
    fclose(fout);

    printf("Filtered data written to %s\n", outfile);
    return 0;
}