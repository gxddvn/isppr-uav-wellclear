from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton

class ModelBrowser(QWidget):
    """Панель для вибору/завантаження моделей (заглушка)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Список моделей"))
        self.list = QListWidget()
        layout.addWidget(self.list)
        layout.addWidget(QPushButton("Додати модель"))
        layout.addStretch()
