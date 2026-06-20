import numpy as np


class SignalPreprocessor:

    def __init__(
        self,
        window_size=256,
        stride=64
    ):

        self.window_size = window_size
        self.stride = stride

    def scale_pair(
        self,
        noisy_signal,
        clean_signal
    ):

        noisy_signal = noisy_signal.astype(
            np.float32
        )

        clean_signal = clean_signal.astype(
            np.float32
        )

        global_min = min(
            noisy_signal.min(),
            clean_signal.min()
        )

        global_max = max(
            noisy_signal.max(),
            clean_signal.max()
        )

        scale = (
            global_max - global_min
        )

        if scale == 0:
            scale = 1.0

        noisy_scaled = (
            noisy_signal - global_min
        ) / scale

        clean_scaled = (
            clean_signal - global_min
        ) / scale

        return (
            noisy_scaled,
            clean_scaled,
            global_min,
            global_max
        )

    def inverse_scale(
        self,
        signal,
        global_min,
        global_max
    ):

        return signal * (
            global_max - global_min
        ) + global_min

    def create_windows(
        self,
        signal
    ):

        windows = []

        for i in range(
            0,
            len(signal) - self.window_size,
            self.stride
        ):

            windows.append(
                signal[
                    i:i+self.window_size
                ]
            )

        return np.array(
            windows,
            dtype=np.float32
        )

    def prepare_pair(
        self,
        noisy_signal,
        clean_signal
    ):

        (
            noisy_signal,
            clean_signal,
            _,
            _
        ) = self.scale_pair(
            noisy_signal,
            clean_signal
        )

        x = self.create_windows(
            noisy_signal
        )

        y = self.create_windows(
            clean_signal
        )

        return x, y