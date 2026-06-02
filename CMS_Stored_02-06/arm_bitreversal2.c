#include "arm_math.h"

/**
 * @brief Bit reversal function for 32-bit data (floating point).
 *        Used internally by CMSIS-DSP FFT functions.
 */
void arm_bitreversal_32(
    uint32_t *pSrc,
    const uint16_t bitRevLen,
    const uint16_t *pBitRevTable)
{
    uint32_t i, a, b, t;

    for (i = 0; i < bitRevLen; i += 2)
    {
        a = pBitRevTable[i];
        b = pBitRevTable[i + 1];

        t = pSrc[a];
        pSrc[a] = pSrc[b];
        pSrc[b] = t;
    }
}
