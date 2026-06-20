import tensorflow as tf


def build_model():

    inputs = tf.keras.Input(
        shape=(256, 1)
    )

    x = tf.keras.layers.Conv1D(
        32,
        5,
        activation="relu",
        padding="same"
    )(inputs)

    x = tf.keras.layers.BatchNormalization()(x)

    x = tf.keras.layers.Conv1D(
        64,
        5,
        activation="relu",
        padding="same"
    )(x)

    x = tf.keras.layers.BatchNormalization()(x)

    x = tf.keras.layers.Conv1D(
        128,
        5,
        activation="relu",
        padding="same"
    )(x)

    x = tf.keras.layers.Dropout(0.2)(x)

    x = tf.keras.layers.Conv1D(
        64,
        5,
        activation="relu",
        padding="same"
    )(x)

    outputs = tf.keras.layers.Conv1D(
        1,
        5,
        padding="same"
    )(x)

    model = tf.keras.Model(
        inputs,
        outputs
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=1e-4
        ),
        loss="mse",
        metrics=["mae"]
    )

    return model