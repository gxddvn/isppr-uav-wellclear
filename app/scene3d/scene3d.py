import os
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *

from .camera import apply_camera, set_projection
from .draw_utils import draw_grid, draw_outline, draw_axis_gizmo, draw_trajectory, create_display_list
from .model_loader import load_gltf_model
from .picking import pick_model_at, cursor_on_gizmo, detect_gizmo_axis
from .mouse_events import SceneMouseHandler


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
        self.pan_sensitivity = 0.2  

        # Моделі
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        try:
            self.uav_mesh = load_gltf_model(os.path.join(BASE_DIR, r"assets\models\uav", "scene.gltf"))
            self.plane_mesh = load_gltf_model(os.path.join(BASE_DIR, r"assets\models\plane", "scene.gltf"))
        except FileNotFoundError as e:
            print(f"[Scene3D] ⚠️ Model load failed: {e}")
            self.uav_mesh = None
            self.plane_mesh = None

        self.uav_pos = [0.0, 0.0, 0.0]
        self.plane_pos = [150.0, 0.0, -50.0]
        self.uav_yaw = 0.0
        self.plane_yaw = 180.0

        self.uav_list = None
        self.plane_list = None

        # Стани миші/гізмо
        self.selected = None
        self.last_mouse_pos = None
        self.is_dragging_model = False
        self.is_rotating_model = False
        self.is_rotating_camera = False
        self.drag_win_z = None
        self.drag_axis = None
        self.allow_mouse_pick = True

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

        if self.uav_mesh:
            self.uav_list = create_display_list(self.uav_mesh)
        if self.plane_mesh:
            self.plane_list = create_display_list(self.plane_mesh)

    def resizeGL(self, w, h):
        set_projection(w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        apply_camera(self)

        draw_grid()

        # UAV
        if self.uav_list:
            glPushMatrix()
            glTranslatef(*self.uav_pos)
            glRotatef(self.uav_yaw, 0, 1, 0)
            glColor3f(0.8, 0.8, 0.8)
            glCallList(self.uav_list)
            glPopMatrix()

        # Plane
        if self.plane_list:
            glPushMatrix()
            glTranslatef(*self.plane_pos)
            glRotatef(self.plane_yaw, 0, 1, 0)
            glColor3f(0.9, 0.4, 0.4)
            glCallList(self.plane_list)
            glPopMatrix()

        # Вибрана модель
        if self.selected == 'uav' and self.uav_list:
            draw_outline(self.uav_list, self.uav_pos, self.uav_yaw)
            draw_axis_gizmo(self.uav_pos)
        elif self.selected == 'plane' and self.plane_list:
            draw_outline(self.plane_list, self.plane_pos, self.plane_yaw)
            draw_axis_gizmo(self.plane_pos)

        # Траєкторії
        if self.uav_list:
            draw_trajectory(self.uav_pos, self.uav_yaw, (0.2, 1.0, 0.2))
        if self.plane_list:
            draw_trajectory(self.plane_pos, self.plane_yaw, (1.0, 0.4, 0.4))
