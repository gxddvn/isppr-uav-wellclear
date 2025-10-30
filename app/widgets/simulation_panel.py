from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal

class SimulationPanel(QWidget):
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    speed_changed = pyqtSignal(float)

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

        # 🔹 Виклики сигналів
        self.btn_start.clicked.connect(lambda: self.start_clicked.emit())
        self.btn_pause.clicked.connect(lambda: self.pause_clicked.emit())
        self.btn_stop.clicked.connect(lambda: self.stop_clicked.emit())
        self.speed_slider.valueChanged.connect(
            lambda val: self.speed_changed.emit(val / 5.0)
        )
