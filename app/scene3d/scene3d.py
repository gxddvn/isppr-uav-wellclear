import os
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *

from .camera import apply_camera, set_projection
from .draw_utils import draw_grid, draw_outline, draw_axis_gizmo, draw_trajectory, create_display_list
from .model_loader import load_gltf_model
from .mouse_events import SceneMouseHandler
from .base_model import BaseModel3D
from .uav import UAV
from .obstacle import Obstacle

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
            self.objects.append(UAV("UAV #1", self.mesh_uav, [0.0, 0.0, 0.0], [0, 0, 0]))
        if self.mesh_plane:
            self.objects.append(Obstacle("Plane #1", self.mesh_plane, [150.0, 0.0, -50.0], [0, 0, 0]))


        # --- Поточний вибір ---
        self.selected = None

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

