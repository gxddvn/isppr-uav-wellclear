from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt

class ModelBrowser(QWidget):
    """Панель для вибору / додавання моделей у сцену."""
    def __init__(self, scene3d, parent=None):
        super().__init__(parent)
        self.scene3d = scene3d

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Список моделей:"))
        self.list = QListWidget()
        layout.addWidget(self.list)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        self.btn_add_uav = QPushButton("➕ Додати UAV")
        self.btn_add_plane = QPushButton("➕ Додати перешкоду")
        btn_layout.addWidget(self.btn_add_uav)
        btn_layout.addWidget(self.btn_add_plane)
        layout.addLayout(btn_layout)

        layout.addStretch()

        # --- Події ---
        self.list.currentTextChanged.connect(self.on_model_selected)
        self.btn_add_uav.clicked.connect(lambda: self.add_model("UAV"))
        self.btn_add_plane.clicked.connect(lambda: self.add_model("Obstacle"))

        # Ініціалізуємо список на старті
        self.refresh_list()

    # ------------------------------------------------------------------
    def refresh_list(self):
        """Оновити список моделей з поточної сцени."""
        self.list.clear()
        for obj in self.scene3d.objects:
            self.list.addItem(obj.name)

    # ------------------------------------------------------------------
    def on_model_selected(self, name):
        """Коли користувач вибрав модель у списку."""
        if not name:
            return  # 🟢 ігноруємо пусті значення, які приходять при оновленні списку

        for obj in self.scene3d.objects:
            if obj.name == name:
                self.scene3d.select_model(obj)
                return

        QMessageBox.warning(self, "Помилка", f"Модель '{name}' не знайдена у сцені.")


    # ------------------------------------------------------------------
    def add_model(self, model_type: str):
        """Додає нову модель у сцену та оновлює список."""
        model = self.scene3d.add_model(model_type)
        if model:
            self.refresh_list()
            # знайти елемент за текстом
            items = self.list.findItems(model.name, Qt.MatchFlag.MatchExactly)
            if items:
                self.list.setCurrentItem(items[0])

