import os
import numpy as np
import pandas as pd
import tensorflow as tf

from signal_loader import ADCDataset
from preprocessing import SignalPreprocessor
from metrics import SignalMetrics


def reconstruct_signal(
    windows,
    signal_length,
    window_size=256,
    stride=64
):

    reconstructed = np.zeros(
        signal_length,
        dtype=np.float32
    )

    counts = np.zeros(
        signal_length,
        dtype=np.float32
    )

    idx = 0

    for start in range(
        0,
        signal_length - window_size,
        stride
    ):

        reconstructed[
            start:start+window_size
        ] += windows[idx]

        counts[
            start:start+window_size
        ] += 1

        idx += 1

    counts[counts == 0] = 1

    return reconstructed / counts


loader = ADCDataset(
    "adc_data"
)

files = loader.scan()

model = tf.keras.models.load_model(
    "models/loadcell_denoiser.keras"
)

prep = SignalPreprocessor(
    window_size=256,
    stride=64
)

reference_file = None

for f in files:

    if f["frequency"] == 0:
        reference_file = f
        break

reference_signal = loader.load_adc_file(
    reference_file["path"]
)

results = []

for f in files:

    if f["frequency"] == 0:
        continue

    print(
        f"Processing {f['frequency']}Hz"
    )

    noisy_signal = loader.load_adc_file(
        f["path"]
    )

    min_len = min(
        len(noisy_signal),
        len(reference_signal)
    )

    noisy_signal = noisy_signal[:min_len]
    clean_signal = reference_signal[:min_len]

    (
        noisy_scaled,
        clean_scaled,
        global_min,
        global_max
    ) = prep.scale_pair(
        noisy_signal,
        clean_signal
    )

    x = prep.create_windows(
        noisy_scaled
    )

    x = x.reshape(
        x.shape[0],
        x.shape[1],
        1
    )

    pred = model.predict(
        x,
        verbose=0
    )

    pred = pred.squeeze()

    cnn_signal = reconstruct_signal(
        pred,
        len(noisy_scaled),
        256,
        64
    )

    cnn_signal = prep.inverse_scale(
        cnn_signal,
        global_min,
        global_max
    )

    raw_mae = SignalMetrics.mae(
        clean_signal,
        noisy_signal
    )

    cnn_mae = SignalMetrics.mae(
        clean_signal,
        cnn_signal
    )

    raw_rmse = SignalMetrics.rmse(
        clean_signal,
        noisy_signal
    )

    cnn_rmse = SignalMetrics.rmse(
        clean_signal,
        cnn_signal
    )

    raw_corr = SignalMetrics.correlation(
        clean_signal,
        noisy_signal
    )

    cnn_corr = SignalMetrics.correlation(
        clean_signal,
        cnn_signal
    )

    results.append({

        "Frequency":
        f["frequency"],

        "Raw_MAE":
        raw_mae,

        "CNN_MAE":
        cnn_mae,

        "Raw_RMSE":
        raw_rmse,

        "CNN_RMSE":
        cnn_rmse,

        "Raw_Correlation":
        raw_corr,

        "CNN_Correlation":
        cnn_corr

    })

df = pd.DataFrame(
    results
)

os.makedirs(
    "reports",
    exist_ok=True
)

df.to_csv(
    "reports/cnn_results.csv",
    index=False
)

print()
print(df)

print()
print(
    "Saved -> reports/cnn_results.csv"
)