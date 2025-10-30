import os
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtWidgets import QMessageBox

from .camera import apply_camera, set_projection
from .draw_utils import draw_grid, draw_outline, draw_axis_gizmo, draw_trajectory, create_display_list
from .model_loader import load_gltf_model
from .mouse_events import SceneMouseHandler
from .base_model import BaseModel3D
from .uav import UAV
from .obstacle import Obstacle
import math

class Scene3D(QOpenGLWidget, SceneMouseHandler):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Камера
        self.camera_distance = 400.0
        self.camera_yaw = -180.0
        self.camera_pitch = 25.0
        self.rotate_sensitivity = 0.5
        self.initial_states = {}

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            self.mesh_uav = load_gltf_model(os.path.join(BASE_DIR, r"assets\models\uav", "scene.gltf"))
            self.mesh_plane = load_gltf_model(os.path.join(BASE_DIR, r"assets\models\plane", "scene.gltf"))
        except FileNotFoundError as e:
            print(f"[Scene3D] ⚠️ Model load failed: {e}")
            self.mesh_uav = None
            self.mesh_plane = None

        # --- Масив моделей у сцені ---
        self.objects = []
        if self.mesh_uav:
            self.objects.append(UAV("UAV #1", self.mesh_uav,))
        if self.mesh_plane:
            self.objects.append(Obstacle("Plane #1", self.mesh_plane,))

        # --- Ініціалізація стартових координат ---
        for obj in self.objects:
            self.initial_states[obj.name] = (obj.position.copy(), obj.rotation.copy())

        # --- Поточний вибір ---
        self.selected = None

        # --- Симуляція ---
        self.is_simulating = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation_step)
        self.sim_speed = 1.0  # множник швидкості
        self.apply_model_altitudes()

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.12, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glShadeModel(GL_SMOOTH)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])

        for obj in self.objects:
            if obj.mesh:
                obj.display_list = create_display_list(obj.mesh)

    def resizeGL(self, w, h):
        set_projection(w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        apply_camera(self)

        draw_grid()

        for obj in self.objects:
            obj.draw(selected=(self.selected == obj))

        # --- Траєкторії для UAV та Obstacle ---
        for obj in self.objects:
            obj.draw_trajectory()
    
    def add_model(self, model_type: str):
        """Додає нову модель до сцени."""
        if model_type == "UAV":
            mesh = self.mesh_uav
            model = UAV(f"UAV #{len([o for o in self.objects if isinstance(o, UAV)]) + 1}", mesh, [0, 0, 0], [0, 0, 0])
        else:
            mesh = self.mesh_plane
            model = Obstacle(f"Obstacle #{len([o for o in self.objects if isinstance(o, Obstacle)]) + 1}", mesh, [0, 0, 0], [0, 0, 0])

        if not mesh:
            print(f"[Scene3D] ❌ Mesh for {model_type} not loaded")
            return None

        model.display_list = create_display_list(mesh)
        self.objects.append(model)
        self.update()
        return model

    def select_model(self, obj: BaseModel3D):
        """Вибір моделі зі сцени."""
        self.selected = obj
        self.update()

    def update_initial_state(self, obj: BaseModel3D):
        """Оновлює початкову позицію та поворот моделі після drag/rotate."""
        self.initial_states[obj.name] = (obj.position.copy(), obj.rotation.copy())

    def start_simulation(self):
        if not self.can_start_simulation():
            QMessageBox.warning(self, "Помилка", "Не всі моделі мають швидкість і висоту!")
            return
        self.is_simulating = True
        self.timer.start(50)  # оновлення кожні 50 мс (~20 FPS)
        print("[Simulation] ▶ Запущено")

    def pause_simulation(self):
        self.is_simulating = False
        self.timer.stop()
        print("[Simulation] ⏸ Пауза")

    def stop_simulation(self):
        self.is_simulating = False
        self.timer.stop()
        for obj in self.objects:
            if obj.name in self.initial_states:
                pos, rot = self.initial_states[obj.name]
                obj.position = pos.copy()
                obj.rotation = rot.copy()
        self.update()
        print("[Simulation] ⏹ Зупинено")


    def can_start_simulation(self):
        """Перевірка, чи всі об’єкти мають speed і altitude"""
        for obj in self.objects:
            if obj.speed <= 0 or obj.altitude <= 0:
                return False
        return True

    def update_simulation_step(self):
        """Оновлення позицій об’єктів у часі"""
        for obj in self.objects:
            if isinstance(obj, (UAV, Obstacle)):
                self.move_model(obj)
        self.update()
    
    def get_movement_vector(self, obj):
        """
        Переводим локальный move_vector в мировую систему
        с учётом текущего yaw модели
        """
        yaw_rad = math.radians(-obj.rotation[1])
        lx, ly, lz = obj.move_vector

        fx = math.cos(yaw_rad) * lx - math.sin(yaw_rad) * lz
        fz = math.sin(yaw_rad) * lx + math.cos(yaw_rad) * lz
        fy = ly
        return [fx, fy, fz]


    def move_model(self, obj):
        speed_ms = (obj.speed / 3.6) * 0.05 * self.sim_speed
        fx, fy, fz = self.get_movement_vector(obj)

        obj.position[0] += fx * speed_ms
        obj.position[1] = obj.altitude
        obj.position[2] += fz * speed_ms

    def apply_model_altitudes(self):
        """Оновлює висоту моделей відповідно до параметрів altitude."""
        for obj in self.objects:
            obj.position[1] = obj.altitude
        self.update()


