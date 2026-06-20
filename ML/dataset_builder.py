import numpy as np

from signal_loader import ADCDataset
from preprocessing import SignalPreprocessor


class DatasetBuilder:

    def __init__(
        self,
        dataset_dir
    ):
        self.dataset_dir = dataset_dir

    def build(self):

        loader = ADCDataset(
            self.dataset_dir
        )

        files = loader.scan()

        clean_file = None

        for f in files:

            if f["frequency"] == 0:

                clean_file = f

                break

        if clean_file is None:

            raise Exception(
                "0Hz reference file not found"
            )

        clean_signal = loader.load_adc_file(
            clean_file["path"]
        )

        prep = SignalPreprocessor(
            window_size=256,
            stride=64
        )

        x_all = []
        y_all = []

        for f in files:

            if f["frequency"] == 0:

                continue

            noisy_signal = loader.load_adc_file(
                f["path"]
            )

            min_len = min(
                len(noisy_signal),
                len(clean_signal)
            )

            noisy_signal = noisy_signal[:min_len]
            clean_signal = clean_signal[:min_len]

            x, y = prep.prepare_pair(
                noisy_signal,
                clean_signal
            )

            count = min(
                len(x),
                len(y)
            )

            x_all.append(
                x[:count]
            )

            y_all.append(
                y[:count]
            )

            print(
                f"Loaded {f['frequency']}Hz"
            )

        X = np.vstack(x_all)
        Y = np.vstack(y_all)

        X = X.reshape(
            X.shape[0],
            X.shape[1],
            1
        )

        Y = Y.reshape(
            Y.shape[0],
            Y.shape[1],
            1
        )

        print()

        print("Training samples:", X.shape)

        return X, Y