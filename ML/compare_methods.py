import pandas as pd

from signal_loader import ADCDataset
from filters import SignalFilters
from metrics import SignalMetrics


loader = ADCDataset(
    "adc_data"
)

files = loader.scan()

reference = None

for f in files:

    if f["frequency"] == 0:

        reference = loader.load_adc_file(
            f["path"]
        )

        break

results = []

for f in files:

    if f["frequency"] == 0:
        continue

    signal = loader.load_adc_file(
        f["path"]
    )

    n = min(
        len(signal),
        len(reference)
    )

    signal = signal[:n]
    ref = reference[:n]

    fir = SignalFilters.fir(signal)

    fft = SignalFilters.fft_filter(signal)

    butter = SignalFilters.butterworth(signal)

    wavelet = SignalFilters.wavelet(signal)

    results.append({

        "Frequency":
        f["frequency"],

        "Raw_MAE":
        SignalMetrics.mae(
            ref,
            signal
        ),

        "FIR_MAE":
        SignalMetrics.mae(
            ref,
            fir
        ),

        "FFT_MAE":
        SignalMetrics.mae(
            ref,
            fft
        ),

        "Butter_MAE":
        SignalMetrics.mae(
            ref,
            butter
        ),

        "Wavelet_MAE":
        SignalMetrics.mae(
            ref,
            wavelet
        )
    })

df = pd.DataFrame(
    results
)

df.to_csv(
    "reports/filter_comparison.csv",
    index=False
)

print(df)