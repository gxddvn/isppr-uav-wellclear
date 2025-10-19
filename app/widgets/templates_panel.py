from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton

class TemplatesPanel(QWidget):
    """Керування шаблонами (заглушка)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Шаблони симуляцій"))
        self.list = QListWidget()
        layout.addWidget(self.list)
        layout.addWidget(QPushButton("Завантажити шаблон"))
        layout.addWidget(QPushButton("Зберегти шаблон"))
        layout.addStretch()
