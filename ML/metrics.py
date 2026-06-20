import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


class SignalMetrics:

    @staticmethod
    def mae(y_true, y_pred):

        return mean_absolute_error(
            y_true,
            y_pred
        )

    @staticmethod
    def mse(y_true, y_pred):

        return mean_squared_error(
            y_true,
            y_pred
        )

    @staticmethod
    def rmse(y_true, y_pred):

        return np.sqrt(
            mean_squared_error(
                y_true,
                y_pred
            )
        )

    @staticmethod
    def r2(y_true, y_pred):

        return r2_score(
            y_true,
            y_pred
        )

    @staticmethod
    def snr(signal, noise):

        signal_power = np.mean(
            signal ** 2
        )

        noise_power = np.mean(
            noise ** 2
        )

        return 10 * np.log10(
            signal_power /
            (noise_power + 1e-12)
        )

    @staticmethod
    def psnr(reference, prediction):

        mse = np.mean(
            (reference - prediction) ** 2
        )

        if mse == 0:
            return 100

        max_val = np.max(reference)

        return 20 * np.log10(
            max_val /
            np.sqrt(mse)
        )

    @staticmethod
    def correlation(
        y_true,
        y_pred
    ):

        return np.corrcoef(
            y_true,
            y_pred
        )[0,1]