from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton

class PropertiesPanel(QWidget):
    """Редактор параметрів об'єкта (заглушка)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Параметри моделі"))
        form = QFormLayout()
        form.addRow("Назва:", QLineEdit())
        form.addRow("Швидкість:", QLineEdit())
        form.addRow("Висота:", QLineEdit())
        layout.addLayout(form)
        layout.addWidget(QPushButton("Застосувати"))
        layout.addStretch()
