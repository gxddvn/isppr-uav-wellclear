import os
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtWidgets import QMessageBox

from .camera import apply_camera, set_projection
from .draw_utils import draw_grid, draw_outline, draw_axis_gizmo, draw_trajectory, create_display_list, draw_cube
from .model_loader import load_gltf_model
from .mouse_events import SceneMouseHandler
from .base_model import BaseModel3D
from .uav import UAV
from .obstacle import Obstacle
from core.risk_model import compute_distance, compute_alt_diff, compute_heading_diff, wald, hurwicz, laplace, savage, compute_collaborative_risk, hybrid_decision
import math
import numpy as np
import copy


class Scene3D(QOpenGLWidget, SceneMouseHandler):
    def __init__(self, parent=None, ml_system=None, log_func=print):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.ml_system = ml_system
        self.log_func = log_func

        # Камера
        self.camera_distance = 400.0
        self.camera_yaw = -180.0
        self.camera_pitch = 25.0
        self.rotate_sensitivity = 0.5
        self.initial_states = {}
        self.min_altitude = 0.0
        # Мінімальний додатковий запас над min_altitude (щоб не сідати прямо на min)
        self.min_altitude_margin = 5.0  # м — змінюй при потребі

        # Мінімальний вертикальний буфер від перешкоди (щоб не наближатися в висоті)
        self.min_vertical_buffer = 5.0  # м — якщо маневр опускає нижче obs.altitude + buffer -> великий штраф


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

    def generate_unique_name(self, base_name: str) -> str:
        """
        Генерує унікальне ім'я для нового об'єкта.
        Наприклад: UAV #1, UAV #2, Obstacle #1, Obstacle #2.
        """
        existing_names = {obj.name for obj in self.objects}
        counter = 1
        name = f"{base_name} #{counter}"
        while name in existing_names:
            counter += 1
            name = f"{base_name} #{counter}"
        return name

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

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
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

        # --- Червона зона обмеження ---
        self.draw_min_altitude_zone()

        for obj in self.objects:
            obj.draw(selected=(self.selected == obj))

        # --- Траєкторії для UAV та Obstacle ---
        for obj in self.objects:
            obj.draw_trajectory()

    def draw_min_altitude_zone(self):
        """Малює червону прозору зону, нижче якої політ заборонений."""
        if self.min_altitude <= 0:
            return

        scene_size = 1000.0
        height = self.min_altitude

        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glColor4f(1.0, 0.0, 0.0, 0.25)
        glPushMatrix()
        glTranslatef(0.0, height / 2.0, 0.0)
        glScalef(scene_size, height, scene_size)
        draw_cube(1.0)  # імпортований з draw_utils
        glPopMatrix()

        glEnable(GL_LIGHTING)

    def add_model(self, model_type: str):
        """Додає нову модель до сцени."""
        if model_type == "UAV":
            mesh = self.mesh_uav
            name = self.generate_unique_name("UAV")
            model = UAV(name, mesh, [0, 0, 0], [0, 0, 0])
        else:
            mesh = self.mesh_plane
            name = self.generate_unique_name("Obstacle")
            model = Obstacle(name, mesh, [0, 0, 0], [0, 0, 0])

        if not mesh:
            print(f"[Scene3D] ❌ Mesh for {model_type} not loaded")
            return None

        model.display_list = create_display_list(mesh)
        self.objects.append(model)
        self.update()
        return model

    def get_objects_data(self):
        """Отримує дані про всі об’єкти на сцені."""
        data = []
        for obj in self.objects:
            data.append({
                "id": obj.name,
                "type": obj.__class__.__name__,
                "position": list(obj.position),
                "rotation": list(obj.rotation),
                "altitude": getattr(obj, "altitude", 0),
                "speed": getattr(obj, "speed", 0),
                "move_vector": list(getattr(obj, "move_vector", [0,0,0]))
            })
        return data

    def load_objects_from_template(self, objects_data):
        """Очищає сцену та відновлює об’єкти із шаблону."""
        print("[TEMPLATE] Завантаження шаблону...")
        self.objects.clear()
        self.objects = []

        for obj_data in objects_data:
            model_type = obj_data["type"]
            name = obj_data["id"]
            position = obj_data["position"]
            rotation = obj_data["rotation"]

            altitude = obj_data.get("altitude", position[1])
            speed = obj_data.get("speed", 0.0)
            move_vector = obj_data.get("move_vector", [0, 0, 1])

            if model_type == "UAV":
                mesh = self.mesh_uav
                obj = UAV(name, mesh, position, rotation)
            elif model_type == "Obstacle":
                mesh = self.mesh_plane
                obj = Obstacle(name, mesh, position, rotation)
            else:
                print(f"[TEMPLATE] ⚠️ Невідомий тип: {model_type}")
                continue

            obj.altitude = altitude
            obj.speed = speed
            obj.move_vector = move_vector

            if mesh:
                obj.display_list = create_display_list(mesh)

            self.objects.append(obj)
            print(f"[TEMPLATE] ✅ Додано {name}: alt={altitude}, speed={speed}, mv={move_vector}")

        # 🔹 Оновлюємо початковий стан для Stop
        self.initial_states.clear()
        for obj in self.objects:
            self.initial_states[obj.name] = (obj.position.copy(), obj.rotation.copy())

        # Оновлюємо позиції по висотах і перемальовуємо
        self.apply_model_altitudes()
        self.update()

        # ✅ Оновлення списку у ModelBrowser
        if hasattr(self, 'model_browser') and self.model_browser:
            self.model_browser.refresh_list()
            if self.model_browser.list.count() > 0:
                self.model_browser.list.setCurrentRow(0)

        self.refresh_model_list()
        print("[TEMPLATE] Завантаження завершено.")

    def refresh_model_list(self):
        """Оновлює список моделей у панелі керування або селекті."""
        self.model_list = [obj.name for obj in self.objects]  # якщо потрібен список імен
        # Якщо є UI-селект:
        if hasattr(self, 'model_select_widget'):
            self.model_select_widget.clear()
            self.model_select_widget.addItems(self.model_list)
        print("[UI] Список моделей оновлено.")

    def select_model(self, obj: BaseModel3D):
        """Вибір моделі зі сцени."""
        self.selected = obj
        self.update()

    def update_initial_state(self, obj: BaseModel3D):
        """Оновлює початкову позицію та поворот моделі після змін."""
        # 🔹 Синхронізуємо позицію з висотою перед збереженням
        obj.position[1] = obj.altitude
        self.initial_states[obj.name] = (obj.position.copy(), obj.rotation.copy())
        print(f"[STATE] updated initial state for {obj.name}: pos={obj.position}, alt={obj.altitude}")


    def start_simulation(self):
        if not self.can_start_simulation():
            QMessageBox.warning(self, "Помилка", "Не всі моделі мають швидкість і висоту!")
            return

        for obj in self.objects:
            print(f"obj.name: {obj.name}")
            print(f"obj.position[1]: {obj.position[1]}")
            print(f"obj.altitude: {obj.altitude}")
            print(f"self.min_altitude: {self.min_altitude}")
            if obj.position[1] < self.min_altitude:
                QMessageBox.warning(self, "Помилка", f"Модель {obj.name} знаходиться нижче мінімальної висоти {self.min_altitude} м!")
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

    def set_min_altitude(self, value: float):
        """Задає мінімальну висоту польоту і оновлює сцену."""
        self.min_altitude = value
        self.update()  # щоб червона зона перемальовувалась у реальному часі


    def can_start_simulation(self):
        """Перевірка, чи всі об’єкти мають speed і altitude"""
        for obj in self.objects:
            if obj.speed <= 0 or obj.altitude <= 0:
                return False
        return True
    
    def handle_warning_zone(self, uav, obs):
        """
        Генерує варіанти обходу для оператора і виводить їх у консоль.
        """
        options = [
            {"name": "Підйом", "altitude": uav.altitude + 5},
            {"name": "Спуск", "altitude": max(self.min_altitude, uav.altitude - 5)},
            {"name": "Вліво", "move_vector": [-1, 0, 0]},
            {"name": "Вправо", "move_vector": [1, 0, 0]},
        ]

        # Виводимо в консоль
        self.log_func(f"[WARNING] UAV {uav.name} поруч з перешкодою {obs.name}. Варіанти обходу:")
        for opt in options:
            desc = opt.get("name", "не вказано")
            alt = opt.get("altitude", "—")
            mv = opt.get("move_vector", "—")
            self.log_func(f"   ➤ {desc}: altitude={alt}, move_vector={mv}")

        return options

    def handle_danger_zone(self, uav, obstacles):
        """
        Дрон вибирає маневр з урахуванням мінімальної висоти та оцінює ризики
        через гібридний метод (Wald / Hurwicz / Laplace).
        """
        candidate_moves = [
            {"name": "Підйом", "altitude": uav.altitude + 5, "move_vector": uav.move_vector},
            {"name": "Спуск", "altitude": max(self.min_altitude + 5, uav.altitude - 5), "move_vector": uav.move_vector},
            {"name": "Вліво", "altitude": uav.altitude, "move_vector": [-1, 0, 0]},
            {"name": "Вправо", "altitude": uav.altitude, "move_vector": [1, 0, 0]},
            {"name": "Назад", "altitude": uav.altitude, "move_vector": [0, 0, -1]},
        ]

        # --- Створюємо матрицю ризиків ---
        payoff_matrix = np.zeros((len(candidate_moves), len(obstacles)))
        for i, move in enumerate(candidate_moves):
            temp_uav = copy.deepcopy(uav)
            temp_uav.altitude = move["altitude"]
            temp_uav.move_vector = move["move_vector"]

            for j, obs in enumerate(obstacles):
                base_risk = compute_collaborative_risk(
                    temp_uav, [obs], self.ml_system, gamma=2.0, min_altitude=self.min_altitude
                )

                # 🔹 Штраф за наближення до мінімальної висоти
                altitude_margin = move["altitude"] - self.min_altitude
                if altitude_margin < 10:
                    base_risk += (10 - altitude_margin) * 0.05

                # 🔹 Легкий штраф за надмірний підйом
                if move["altitude"] - uav.altitude > 15:
                    base_risk += 0.1

                payoff_matrix[i, j] = base_risk

        # --- Обчислюємо поточний ризик ---
        current_risk = compute_collaborative_risk(uav, obstacles, self.ml_system, gamma=2.0, min_altitude=self.min_altitude)

        # --- Використовуємо гібридний метод ---
        decision_index, strategy = hybrid_decision(payoff_matrix, current_risk)
        best_move = candidate_moves[decision_index]

        # --- Застосовуємо вибраний маневр ---
        uav.altitude = best_move["altitude"]
        uav.move_vector = best_move["move_vector"]

        print(f"🧭 [DAA] Hybrid strategy: {strategy}")
        print(f"✅ UAV {uav.name}: маневр '{best_move['name']}' (risk={current_risk:.2f})")

    def update_simulation_step(self):
        print("[STEP] === Tick start ===")

        if self.ml_system is None:
            print("[STEP] ❌ ML System не передана — выход")
            return

        uav = next((o for o in self.objects if isinstance(o, UAV)), None)
        obstacles = [o for o in self.objects if isinstance(o, Obstacle)]
        if not uav:
            print("[STEP] ❌ UAV не найден — выход")
            return

        print(f"[STEP] ✅ UAV найден: {uav.name}, obstacles: {len(obstacles)}")

        risk = compute_collaborative_risk(uav, obstacles, self.ml_system, gamma=2.0, min_altitude=self.min_altitude) + 0.5
        print(f"[STEP] 🧠 Collaborative Risk={risk:.2f}")

        if risk < 0.3:
            pass
        elif risk < 0.7:
            for obs in obstacles:
                self.handle_warning_zone(uav, obs)
        else:
            self.handle_danger_zone(uav, obstacles)

        for obj in self.objects:
            if isinstance(obj, (UAV, Obstacle)):
                self.move_model(obj)
                print(f"[STEP] 🔹 Об’єкт '{obj.name}' updated: pos={obj.position}, rot={obj.rotation}")

        self.update()
        print("[STEP] ✅ Кадр оновлено\n")

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
        obj.position[2] += fz * speed_ms
        new_y = max(obj.altitude, self.min_altitude)
        obj.position[1] = new_y
        print(f"[MOVE] {obj.name}: Δx={fx*speed_ms:.2f}, Δz={fz*speed_ms:.2f}, pos={obj.position}")

    def apply_model_altitudes(self):
        """Оновлює висоту моделей відповідно до параметрів altitude."""
        for obj in self.objects:
            obj.position[1] = obj.altitude
        self.update()


