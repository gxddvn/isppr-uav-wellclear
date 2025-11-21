from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel

class ConsolePanel(QWidget):
    """Нижня консоль для логів."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(QLabel("Консоль:"))
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

    def log(self, message: str):
        self.text.append(message)
