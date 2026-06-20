from dataset_builder import DatasetBuilder

builder = DatasetBuilder(
    "adc_data"
)

X, Y = builder.build()

print(X.shape)
print(Y.shape)