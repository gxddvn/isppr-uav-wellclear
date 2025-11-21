from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QHBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from ..scene3d.uav import UAV

class ModelBrowser(QWidget):
    """Панель для вибору / додавання моделей у сцену."""

    # 🟩 Сигнал, який передає вибрану модель або None
    selection_changed = pyqtSignal(object)

    def __init__(self, scene3d, parent=None):
        super().__init__(parent)
        self.scene3d = scene3d

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Список моделей:"))
        self.list = QListWidget()
        layout.addWidget(self.list)

        row1 = QHBoxLayout()
        self.btn_add_uav = QPushButton("➕ Додати UAV")
        self.btn_add_plane = QPushButton("➕ Додати перешкоду")
        row1.addWidget(self.btn_add_uav)
        row1.addWidget(self.btn_add_plane)

        row2 = QHBoxLayout()
        self.btn_add_cylinder = QPushButton("➕ Додати циліндр")
        self.btn_add_sphere = QPushButton("➕ Додати сферу")
        row2.addWidget(self.btn_add_cylinder)
        row2.addWidget(self.btn_add_sphere)

        layout.addLayout(row1)
        layout.addLayout(row2)

        self.btn_delete = QPushButton("🗑 Видалити модель")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("color: gray;")
        layout.addWidget(self.btn_delete)

        layout.addStretch()

        # --- Події ---
        self.list.currentTextChanged.connect(self.on_model_selected)
        self.btn_add_uav.clicked.connect(lambda: self.add_model("UAV"))
        self.btn_add_plane.clicked.connect(lambda: self.add_model("Obstacle"))
        self.btn_add_cylinder.clicked.connect(lambda: self.add_model("Cylinder"))
        self.btn_add_sphere.clicked.connect(lambda: self.add_model("Sphere"))
        self.btn_delete.clicked.connect(self.delete_selected_model)

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
            """)
            self.btn_add_uav.setToolTip("UAV вже існує у сцені — не можна створити другий.")
        else:
            self.btn_add_uav.setEnabled(True)
            self.btn_add_uav.setStyleSheet("")
            self.btn_add_uav.setToolTip("Додати безпілотник (UAV) до сцени.")

    # ------------------------------------------------------------------
    def on_model_selected(self, name):
        """Коли користувач вибрав модель у списку."""
        if not name:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setStyleSheet("color: gray;")
            # 🟩 Передаємо None, якщо нічого не вибрано
            self.selection_changed.emit(None)
            return

        found = False
        for obj in self.scene3d.objects:
            if obj.name == name:
                self.scene3d.select_model(obj)
                # 🟩 Еміт сигнал вибраної моделі
                self.selection_changed.emit(obj)
                found = True
                break

        if found:
            self.btn_delete.setEnabled(True)
            self.btn_delete.setStyleSheet("color: #ff5555;")
            self.btn_delete.setToolTip("Видалити вибрану модель із сцени")
        else:
            QMessageBox.warning(self, "Помилка", f"Модель '{name}' не знайдена у сцені.")
            self.selection_changed.emit(None)

    # ------------------------------------------------------------------
    def add_model(self, model_type: str):
        """Додає нову модель до сцени."""
        if model_type == "UAV" and any(isinstance(o, UAV) for o in self.scene3d.objects):
            print("[Scene3D] ⚠️ Неможливо створити другий UAV — уже існує.")
            return None

        model = self.scene3d.add_model(model_type)
        if model:
            self.refresh_list()

            # знайти елемент за текстом
            items = self.list.findItems(model.name, Qt.MatchFlag.MatchExactly)
            if items:
                self.list.setCurrentItem(items[0])
                # 🟩 Вибрали й емітимо сигнал
                self.selection_changed.emit(model)
        return model

    # ------------------------------------------------------------------
    def delete_selected_model(self):
        """Видаляє поточно вибрану модель зі сцени."""
        selected_name = self.list.currentItem().text() if self.list.currentItem() else None
        if not selected_name:
            QMessageBox.warning(self, "Помилка", "Не вибрано жодної моделі.")
            return

        for obj in self.scene3d.objects:
            if obj.name == selected_name:
                self.scene3d.objects.remove(obj)
                if self.scene3d.selected == obj:
                    self.scene3d.selected = None
                self.scene3d.update()
                break

        # 🟩 Оновлення списку й сигнал
        self.refresh_list()
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("color: gray;")
        self.selection_changed.emit(None)
