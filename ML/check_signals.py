from signal_loader import ADCDataset
import matplotlib.pyplot as plt

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

plt.figure(figsize=(12,6))

plt.plot(
    sig0[:2000],
    label="0Hz"
)

plt.plot(
    sig50[:2000],
    label="50Hz"
)

plt.legend()

plt.show()