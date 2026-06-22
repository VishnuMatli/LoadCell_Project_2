import sys
import os
import numpy as np
import pandas as pd
import tensorflow as tf
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QProgressBar, QTextEdit, QFormLayout, 
                             QSpinBox, QDoubleSpinBox, QHBoxLayout)
from PyQt6.QtCore import QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- Training Worker Thread ---
class TrainingWorker(QThread):
    progress_update = pyqtSignal(int, float)
    finished = pyqtSignal(object, list)

    def __init__(self, model, x_train, y_train, epochs, batch_size):
        super().__init__()
        self.model = model
        self.x_train, self.y_train = x_train, y_train
        self.epochs, self.batch_size = epochs, batch_size
        self.history = []

    def run(self):
        for epoch in range(self.epochs):
            history = self.model.fit(self.x_train, self.y_train, epochs=1, batch_size=self.batch_size, verbose=0)
            loss = history.history['loss'][0]
            self.history.append(loss)
            self.progress_update.emit(int(((epoch + 1) / self.epochs) * 100), loss)
        self.finished.emit(self.model, self.history)

# --- GUI Application ---
class DenoisingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Load Cell Denoising Research Platform")
        self.setGeometry(100, 100, 900, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left Panel: Controls
        control_panel = QVBoxLayout()
        form = QFormLayout()
        self.epochs_input = QSpinBox()
        self.epochs_input.setValue(20)
        self.lr_input = QDoubleSpinBox()
        self.lr_input.setValue(0.001)
        form.addRow("Epochs:", self.epochs_input)
        form.addRow("Learning Rate:", self.lr_input)
        control_panel.addLayout(form)
        
        self.btn_train = QPushButton("Start Training")
        self.btn_train.clicked.connect(self.start_training)
        control_panel.addWidget(self.btn_train)
        
        self.progress = QProgressBar()
        control_panel.addWidget(self.progress)
        
        self.logs = QTextEdit()
        control_panel.addWidget(self.logs)
        main_layout.addLayout(control_panel, 1)
        
        # Right Panel: Plotting
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas, 2)

    def start_training(self):
        self.model = tf.keras.Sequential([
            tf.keras.layers.Conv1D(32, 3, activation='relu', input_shape=(100, 1)), 
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(100)
        ])
        self.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=self.lr_input.value()), loss='mse')
        
        x = np.random.rand(50, 100, 1)
        y = np.random.rand(50, 100)
        
        self.worker = TrainingWorker(self.model, x, y, self.epochs_input.value(), 8)
        self.worker.progress_update.connect(self.update_ui)
        self.worker.finished.connect(self.training_complete)
        self.worker.start()
        self.logs.append("Training started...")

    def update_ui(self, val, loss):
        self.progress.setValue(val)
        self.logs.append(f"Epoch progress: {val}% | Loss: {loss:.6f}")

    def training_complete(self, model, history):
        self.logs.append("Training finished.")
        # Save model
        model.save('denoising_model.keras')
        self.logs.append("Model saved as 'denoising_model.keras'")
        
        # Save history
        pd.DataFrame(history, columns=['loss']).to_csv('training_history.csv', index=False)
        self.logs.append("History saved to 'training_history.csv'")
        
        # Visualize
        ax = self.figure.add_subplot(111)
        ax.clear()
        ax.plot(history)
        ax.set_title("Training Loss Curve")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("MSE Loss")
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DenoisingApp()
    window.show()
    sys.exit(app.exec())