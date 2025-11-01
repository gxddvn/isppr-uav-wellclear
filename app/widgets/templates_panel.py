import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget,
    QPushButton, QFileDialog, QMessageBox
)

class TemplatesPanel(QWidget):
    """Панель керування шаблонами симуляцій."""
    def __init__(self, scene3d, parent=None):
        super().__init__(parent)
        self.scene3d = scene3d

        # 📁 Папка для збереження шаблонів за замовчуванням
        self.templates_dir = os.path.join(os.getcwd(), "templates")
        os.makedirs(self.templates_dir, exist_ok=True)

        # --- UI ---
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Шаблони симуляцій"))

        self.list = QListWidget()
        layout.addWidget(self.list)

        self.btn_load = QPushButton("Завантажити шаблон")
        self.btn_save = QPushButton("Зберегти шаблон")
        self.btn_refresh = QPushButton("🔄 Оновити список")
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_load)
        layout.addWidget(self.btn_refresh)
        layout.addStretch()

        # --- Події ---
        self.btn_save.clicked.connect(self.save_template)
        self.btn_load.clicked.connect(self.load_template_dialog)
        self.btn_refresh.clicked.connect(self.refresh_list)
        self.list.itemDoubleClicked.connect(self.load_selected_template)

        # --- Початкове завантаження ---
        self.refresh_list()

    # ---------------------------------------------------------
    # 📜 Оновлення списку шаблонів у директорії templates
    # ---------------------------------------------------------
    def refresh_list(self):
        self.list.clear()
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)

        files = [f for f in os.listdir(self.templates_dir) if f.endswith(".json")]
        if not files:
            self.list.addItem("— Немає збережених шаблонів —")
            self.list.setEnabled(False)
        else:
            self.list.setEnabled(True)
            for f in sorted(files):
                self.list.addItem(f)
        print(f"[TemplatesPanel] 🔄 Оновлено список шаблонів ({len(files)} знайдено)")

    # ---------------------------------------------------------
    # 💾 Збереження шаблону
    # ---------------------------------------------------------
    def save_template(self):
        # 🔸 Пропонуємо користувачу вибрати шлях, але дефолтно відкриваємо templates/
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Зберегти шаблон",
            os.path.join(self.templates_dir, "New_Template.json"),
            "Template Files (*.json)"
        )
        if not path:
            return

        scene_objects = self.scene3d.get_objects_data()
        template = {
            "name": os.path.basename(path),
            "created_at": datetime.now().isoformat(),
            "objects": scene_objects
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Успішно", f"Шаблон збережено у:\n{path}")
            self.refresh_list()
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти шаблон:\n{e}")

    # ---------------------------------------------------------
    # 📂 Завантаження шаблону через діалог (вибір вручну)
    # ---------------------------------------------------------
    def load_template_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Завантажити шаблон",
            self.templates_dir,
            "Template Files (*.json)"
        )
        if not path:
            return
        self._load_template_from_path(path)

    # ---------------------------------------------------------
    # 📦 Завантаження шаблону при кліку на елемент списку
    # ---------------------------------------------------------
    def load_selected_template(self, item):
        filename = item.text()
        path = os.path.join(self.templates_dir, filename)
        if not os.path.exists(path):
            QMessageBox.warning(self, "Помилка", "Файл шаблону не знайдено!")
            return
        self._load_template_from_path(path)

    # ---------------------------------------------------------
    # 🧠 Реальне завантаження шаблону з JSON
    # ---------------------------------------------------------
    def _load_template_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                template = json.load(f)

            self.scene3d.load_objects_from_template(template["objects"])
            QMessageBox.information(self, "Готово", f"Шаблон '{template['name']}' завантажено!")
            print(f"[TemplatesPanel] ✅ Завантажено шаблон: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити шаблон:\n{e}")
