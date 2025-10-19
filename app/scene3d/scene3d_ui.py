from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox
from .scene3d import Scene3D  # <-- імпорт сцени

class Scene3DWithUI(QWidget):
    def __init__(self):
        super().__init__()
        self.scene3d = Scene3D(self)

        # Список моделей
        self.model_list = QComboBox()
        self.model_list.addItems(['uav', 'plane'])
        self.model_list.currentTextChanged.connect(self.on_model_selected)

        # Розкладка
        layout = QVBoxLayout()
        layout.addWidget(self.scene3d)
        layout.addWidget(self.model_list)
        self.setLayout(layout)

    def on_model_selected(self, name):
        self.scene3d.selected = name
        self.scene3d.allow_mouse_pick = False  # блокувати pick мишею після вибору зі списку
        self.scene3d.update()
