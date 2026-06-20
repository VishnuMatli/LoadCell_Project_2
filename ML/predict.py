import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf

from signal_loader import ADCDataset
from preprocessing import SignalPreprocessor


loader = ADCDataset("adc_data")

files = loader.scan()

sig0 = None
sig50 = None

for f in files:

    if f["frequency"] == 0:
        sig0 = loader.load_adc_file(
            f["path"]
        )

    if f["frequency"] == 50:
        sig50 = loader.load_adc_file(
            f["path"]
        )

prep = SignalPreprocessor(
    window_size=256,
    stride=64
)

(
    noisy_scaled,
    clean_scaled,
    global_min,
    global_max
) = prep.scale_pair(
    sig50,
    sig0
)

windows = prep.create_windows(
    noisy_scaled
)

windows = windows.reshape(
    windows.shape[0],
    windows.shape[1],
    1
)

model = tf.keras.models.load_model(
    "models/loadcell_denoiser.keras"
)

pred = model.predict(windows)

pred_signal = pred.flatten()

pred_signal = prep.inverse_scale(
    pred_signal,
    global_min,
    global_max
)

plt.figure(figsize=(14,6))

plt.plot(
    sig50[:2000],
    label="50Hz Raw",
    alpha=0.7
)

plt.plot(
    sig0[:2000],
    label="0Hz Reference",
    linewidth=2
)

plt.plot(
    pred_signal[:2000],
    label="CNN Output",
    linewidth=2
)

plt.legend()

plt.title(
    "CNN Denoising Result"
)

plt.show()