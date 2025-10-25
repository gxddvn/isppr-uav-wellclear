from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt
from ..scene3d.uav import UAV

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
        self.list.blockSignals(True)
        self.list.clear()
        for obj in self.scene3d.objects:
            self.list.addItem(obj.name)
        self.list.blockSignals(False)

        # --- Перевірка наявності UAV ---
        has_uav = any(isinstance(obj, UAV) for obj in self.scene3d.objects)

        if has_uav:
            self.btn_add_uav.setEnabled(False)
            self.btn_add_uav.setStyleSheet("""
                QPushButton {
                    color: gray;
                    background-color: #2b2b2b;
                    border: 1px solid #555;
                }
            """)  # робимо кнопку сірою
            self.btn_add_uav.setToolTip("UAV вже існує у сцені — не можна створити другий.")
        else:
            self.btn_add_uav.setEnabled(True)
            self.btn_add_uav.setStyleSheet("")  # повертаємо стандартний стиль
            self.btn_add_uav.setToolTip("Додати безпілотник (UAV) до сцени.")



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
        """Додає нову модель до сцени."""
        if model_type == "UAV" and any(isinstance(o, UAV) for o in self.objects):
            print("[Scene3D] ⚠️ Неможливо створити другий UAV — уже існує.")
            return None
        model = self.scene3d.add_model(model_type)
        if model:
            self.refresh_list()
            # знайти елемент за текстом
            items = self.list.findItems(model.name, Qt.MatchFlag.MatchExactly)
            if items:
                self.list.setCurrentItem(items[0])

