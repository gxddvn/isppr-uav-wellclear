import sys, os

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import torch
from ml.ml_system import MLSystem

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QSplitter, QMenuBar, QStatusBar, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

from app.widgets.model_browser import ModelBrowser
from app.widgets.properties_panel import PropertiesPanel
from app.widgets.templates_panel import TemplatesPanel
from app.widgets.console_panel import ConsolePanel
from app.widgets.simulation_panel import SimulationPanel
from app.scene3d.scene3d import Scene3D

class MainWindow(QMainWindow):
    def __init__(self, ml_system=None):
        super().__init__()
        self.setWindowTitle("ISPPR-BPLA")
        self.resize(1280, 720)

        # === Меню ===
        self._create_menu()

        # === Центральна зона ===
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # === Верхня частина: сцена + панелі ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=10)

        # === Нижня частина: консоль ===
        self.console = ConsolePanel()
        main_layout.addWidget(self.console, stretch=2)

        # === Ініціалізація AI ===
        if ml_system is not None:
            self.ml_system = ml_system
        else:
            from ml.ml_system import MLSystem
            self.ml_system = MLSystem(log_func=self.console.log)

        #ТЕСТ Приклад використання:
        v1, v2, heading1, heading2, distance, alt1, alt2 = 30, 25, 10, 20, 400, 100, 110

        # Вычисляем новые признаки
        alt_diff = alt1 - alt2
        heading_diff = (heading1 - heading2 + 180) % 360 - 180  # разница в диапазоне [-180, 180]
        speed_diff = v1 - v2

        # Полный список признаков для модели
        features = [v1, v2, heading1, heading2, distance, alt1, alt2, alt_diff, heading_diff, speed_diff]

        risk = ml_system.predict(features)
        print(f"Collision risk: {risk:.2f}")
        
        # Сцена (центр)
        self.scene3d = Scene3D(self, ml_system=self.ml_system, log_func=self.console.log)
        splitter.addWidget(self.scene3d)
        
        # Ліва панель з вкладками
        left_tabs = QTabWidget()
        self.model_browser = ModelBrowser(self.scene3d)
        self.properties_panel = PropertiesPanel()
        self.templates_panel = TemplatesPanel(scene3d=self.scene3d)
        left_tabs.addTab(self.model_browser, "Моделі")
        left_tabs.addTab(self.properties_panel, "Параметри")
        left_tabs.addTab(self.templates_panel, "Шаблони")
        splitter.addWidget(left_tabs)
        self.scene3d.model_browser = self.model_browser

        self.model_browser.selection_changed.connect(self.properties_panel.set_model)
        self.properties_panel.model_updated.connect(self.scene3d.update_initial_state)

        # додаємо зв'язок для оновлення висоти моделі
        self.properties_panel.model_updated.connect(self.on_model_updated)

        # Панель управління симуляцією (справа)
        self.sim_panel = SimulationPanel()
        splitter.addWidget(self.sim_panel)

        splitter.setSizes([250, 900, 250])

        # === Статусбар ===
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")
        self.model_browser.refresh_list()
        self.sim_panel.start_clicked.connect(lambda: self.status_bar.showMessage("Симуляцію запущено"))
        self.sim_panel.pause_clicked.connect(lambda: self.status_bar.showMessage("Симуляцію призупинено"))
        self.sim_panel.stop_clicked.connect(lambda: self.status_bar.showMessage("Симуляцію зупинено"))

        self.sim_panel.start_clicked.connect(self.scene3d.start_simulation)
        self.sim_panel.pause_clicked.connect(self.scene3d.pause_simulation)
        self.sim_panel.stop_clicked.connect(self.scene3d.stop_simulation)

        self.sim_panel.min_altitude_changed.connect(self.scene3d.set_min_altitude)

        # регулювання швидкості
        self.sim_panel.speed_changed.connect(self.on_speed_changed)

    def on_speed_changed(self, speed_factor: float):
        self.scene3d.sim_speed = speed_factor
        self.console.log(f"[Simulation] 🔧 Швидкість ×{speed_factor:.1f}")

    def on_model_updated(self, model):
        # Оновлюємо позицію моделі на сцені
        model.position[1] = model.altitude  # висота
        self.scene3d.update()  # перемалювати сцену

    def _create_menu(self):
        menubar = QMenuBar()
        self.setMenuBar(menubar)

        # === Меню "Файл" ===
        file_menu = menubar.addMenu("Файл")

        action_new = file_menu.addAction("Новий проєкт")
        # action_open = file_menu.addAction("Відкрити...")
        # action_save = file_menu.addAction("Зберегти")
        file_menu.addSeparator()
        action_exit = file_menu.addAction("Вихід")

        action_new.triggered.connect(self.new_project)
        # action_open.triggered.connect(self.open_project)
        # action_save.triggered.connect(self.save_project)
        action_exit.triggered.connect(self.close)

        # === Меню "Вид" ===
        view_menu = menubar.addMenu("Вид")

        toggle_console_action = view_menu.addAction("Показати/сховати консоль")
        toggle_console_action.setCheckable(True)
        toggle_console_action.setChecked(True)
        toggle_console_action.triggered.connect(self.toggle_console)

        # === Меню "Допомога" ===
        help_menu = menubar.addMenu("Допомога")

        about_action = help_menu.addAction("Про програму")
        about_action.triggered.connect(self.show_about)
    
    def new_project(self):
        confirm = QMessageBox.question(
            self,
            "Новий проєкт",
            "Ви впевнені, що хочете створити новий проєкт?\n"
            "Усі поточні моделі та налаштування сцени буде втрачено.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # 🔹 1. Очистити сцену
            self.scene3d.objects.clear()
            self.scene3d.update()

            # 🔹 2. Скинути вибір і властивості
            self.scene3d.selected = None
            self.properties_panel.set_model(None)

            # 🔹 3. Оновити список моделей
            if hasattr(self.model_browser, "refresh_list"):
                self.model_browser.refresh_list()

            # 🔹 4. Лог і статус
            self.console.log("[Файл] Створено новий порожній проєкт")
            self.status_bar.showMessage("Новий проєкт створено")


    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Відкрити файл проєкту", "", "JSON Files (*.json);;All Files (*)")
        if path:
            # TODO: завантажити дані з JSON
            self.console.log(f"[Файл] Відкрито файл: {path}")
            self.status_bar.showMessage(f"Відкрито {path}")

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти проєкт", "", "JSON Files (*.json)")
        if path:
            # TODO: серіалізувати сцену і дані у JSON
            self.console.log(f"[Файл] Збережено проєкт: {path}")
            self.status_bar.showMessage("Проєкт збережено")

    def toggle_console(self, visible: bool):
        self.console.setVisible(visible)
        self.status_bar.showMessage("Консоль приховано" if not visible else "Консоль відображено")

    def show_about(self):
        QMessageBox.information(
            self,
            "Про програму",
            "<b>ISPPR-BPLA</b><br>Система підтримки прийняття рішень оператора БПЛА.<br><br>"
            "Розробник: Грищенко В.С.<br>"
            "Ліцензія: Apache 2.0<br>"
            "© 2025"
        )


if __name__ == "__main__":
    # === Ініціалізація AI ===
    ml_system = MLSystem()

    #ТЕСТ Приклад використання:
    v1, v2, heading1, heading2, distance, alt1, alt2 = 30, 25, 10, 20, 400, 100, 110

    # Вычисляем новые признаки
    alt_diff = alt1 - alt2
    heading_diff = (heading1 - heading2 + 180) % 360 - 180  # разница в диапазоне [-180, 180]
    speed_diff = v1 - v2

    # Полный список признаков для модели
    features = [v1, v2, heading1, heading2, distance, alt1, alt2, alt_diff, heading_diff, speed_diff]

    risk = ml_system.predict(features)
    print(f"Collision risk: {risk:.2f}")

    app = QApplication(sys.argv)
    app.setStyleSheet(open("app/style.qss", encoding="utf-8").read())
    window = MainWindow(ml_system=ml_system)
    window.show()
    sys.exit(app.exec())
