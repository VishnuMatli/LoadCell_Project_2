import os
import numpy as np
import matplotlib.pyplot as plt


class ResearchPlots:

    @staticmethod
    def loss_curve(history):

        plt.figure(figsize=(10,5))

        plt.plot(
            history.history["loss"],
            label="Train"
        )

        plt.plot(
            history.history["val_loss"],
            label="Validation"
        )

        plt.title(
            "Training Loss"
        )

        plt.xlabel(
            "Epoch"
        )

        plt.ylabel(
            "MSE Loss"
        )

        plt.legend()

        os.makedirs(
            "figures",
            exist_ok=True
        )

        plt.savefig(
            "figures/loss_curve.png",
            dpi=300
        )

        plt.close()

    @staticmethod
    def signal_comparison(
        raw,
        reference,
        prediction,
        filename="comparison.png"
    ):

        plt.figure(
            figsize=(14,6)
        )

        plt.plot(
            raw,
            label="Raw"
        )

        plt.plot(
            reference,
            label="Reference"
        )

        plt.plot(
            prediction,
            label="CNN"
        )

        plt.legend()

        plt.title(
            "Signal Comparison"
        )

        os.makedirs(
            "figures",
            exist_ok=True
        )

        plt.savefig(
            f"figures/{filename}",
            dpi=300
        )

        plt.close()

    @staticmethod
    def fft_spectrum(
        signal,
        filename="fft.png"
    ):

        fft = np.abs(
            np.fft.rfft(signal)
        )

        plt.figure(
            figsize=(12,5)
        )

        plt.plot(
            fft
        )

        plt.title(
            "FFT Spectrum"
        )

        os.makedirs(
            "figures",
            exist_ok=True
        )

        plt.savefig(
            f"figures/{filename}",
            dpi=300
        )

        plt.close()