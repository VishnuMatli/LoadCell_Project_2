import os

import tensorflow as tf

from sklearn.model_selection import train_test_split

from dataset_builder import DatasetBuilder
from cnn_model import build_model


print("=" * 60)
print("Loading Dataset")
print("=" * 60)

builder = DatasetBuilder(
    "adc_data"
)

X, Y = builder.build()

print()
print("Dataset Loaded")
print("X Shape:", X.shape)
print("Y Shape:", Y.shape)

print()
print("=" * 60)
print("Splitting Dataset")
print("=" * 60)

x_train, x_test, y_train, y_test = train_test_split(
    X,
    Y,
    test_size=0.20,
    random_state=42
)

print("Train:", x_train.shape)
print("Test :", x_test.shape)

print()
print("=" * 60)
print("Building CNN Model")
print("=" * 60)

model = build_model()

model.summary()

os.makedirs(
    "models",
    exist_ok=True
)

callbacks = [

    tf.keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=10,
        restore_best_weights=True
    ),

    tf.keras.callbacks.ModelCheckpoint(
        "models/best_model.keras",
        monitor="val_loss",
        save_best_only=True
    )

]

print()
print("=" * 60)
print("Training Started")
print("=" * 60)

history = model.fit(

    x_train,
    y_train,

    validation_data=(
        x_test,
        y_test
    ),

    epochs=30,

    batch_size=16,

    callbacks=callbacks,

    verbose=1

)

print()
print("=" * 60)
print("Saving Final Model")
print("=" * 60)

model.save(
    "models/loadcell_denoiser.keras"
)

print("Saved")

print()
print("=" * 60)
print("Evaluating")
print("=" * 60)

loss, mae = model.evaluate(
    x_test,
    y_test,
    verbose=0
)

print(f"Loss : {loss:.6f}")
print(f"MAE  : {mae:.6f}")