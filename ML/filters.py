import numpy as np

from scipy.signal import (
    butter,
    filtfilt,
    firwin,
    lfilter
)

import pywt


class SignalFilters:

    @staticmethod
    def moving_average(
        signal,
        window=5
    ):

        return np.convolve(
            signal,
            np.ones(window)/window,
            mode='same'
        )

    @staticmethod
    def butterworth(
        signal,
        cutoff=10,
        fs=50,
        order=4
    ):

        nyq = 0.5 * fs

        normal_cutoff = (
            cutoff / nyq
        )

        b,a = butter(
            order,
            normal_cutoff,
            btype='low'
        )

        return filtfilt(
            b,
            a,
            signal
        )

    @staticmethod
    def fir(
        signal,
        cutoff=10,
        fs=50,
        taps=101
    ):

        coeffs = firwin(
            taps,
            cutoff,
            fs=fs
        )

        return lfilter(
            coeffs,
            1.0,
            signal
        )

    @staticmethod
    def fft_filter(
        signal,
        keep_percent=0.10
    ):

        fft = np.fft.rfft(signal)

        magnitude = np.abs(fft)

        threshold = np.max(
            magnitude
        ) * keep_percent

        fft[
            magnitude < threshold
        ] = 0

        return np.fft.irfft(
            fft,
            n=len(signal)
        )

    @staticmethod
    def wavelet(
        signal,
        wavelet='db4',
        level=4
    ):

        coeffs = pywt.wavedec(
            signal,
            wavelet,
            level=level
        )

        sigma = np.median(
            np.abs(coeffs[-1])
        ) / 0.6745

        threshold = (
            sigma *
            np.sqrt(
                2 *
                np.log(
                    len(signal)
                )
            )
        )

        coeffs[1:] = [

            pywt.threshold(
                c,
                threshold,
                mode='soft'
            )

            for c in coeffs[1:]
        ]

        return pywt.waverec(
            coeffs,
            wavelet
        )[:len(signal)]