from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal

class SimulationPanel(QWidget):
    """Панель керування симуляцією."""
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Керування симуляцією"))
        self.btn_start = QPushButton("▶ Старт")
        self.btn_pause = QPushButton("⏸ Пауза")
        self.btn_stop = QPushButton("⏹ Стоп")
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_stop)

        layout.addWidget(QLabel("Швидкість симуляції"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        layout.addWidget(self.speed_slider)
        layout.addStretch()

        # сигнали
        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_pause.clicked.connect(self.pause_clicked)
        self.btn_stop.clicked.connect(self.stop_clicked)
