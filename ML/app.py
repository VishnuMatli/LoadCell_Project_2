from signal_loader import ADCDataset

dataset = ADCDataset("adc_data")

files = dataset.scan()

for file in files:

    print(
        file["frequency"],
        file["file"]
    )