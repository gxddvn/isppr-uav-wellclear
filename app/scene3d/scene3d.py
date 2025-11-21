import os
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QInputDialog

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
from .kyiv_map import KyivMapLayer
from core.map_generator import generate_kyiv_map_png, load_kyiv_districts
from .static_obstacle import CylinderModel, SphereModel

class Scene3D(QOpenGLWidget, SceneMouseHandler):
    def __init__(self, parent=None, ml_system=None, log_func=print):
        super().__init__(parent)
        
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        map_path = os.path.join(BASE_DIR, "assets/maps/kyiv_map.png")
        bounds = generate_kyiv_map_png(map_path)
        districts = load_kyiv_districts()

        print(districts[["name", "admin_level"]])

        self.kyiv_map = KyivMapLayer(
            texture_path=map_path,
            geojson_path=os.path.join(BASE_DIR, "assets/maps/kyiv_districts_clean.geojson"),
            bounds=bounds
        )

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

        self.min_altitude_margin = 5.0

        self.min_vertical_buffer = 5.0

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

        self.kyiv_map.load_texture_qt()
        
        for obj in self.objects:
            if obj.mesh:
                obj.display_list = create_display_list(obj.mesh)

    def resizeGL(self, w, h):
        set_projection(w, h)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        apply_camera(self)

        draw_grid(self.kyiv_map, step=500)

        if self.kyiv_map:
            self.kyiv_map.draw()
            self.kyiv_map.draw_min_altitude_boxes()

        for obj in self.objects:
            obj.draw(selected=(self.selected == obj))

        # --- Траєкторії для UAV та Obstacle ---
        for obj in self.objects:
            obj.draw_trajectory()

    def add_model(self, model_type: str):
        model = None

        if model_type == "UAV":
            mesh = self.mesh_uav
            name = self.generate_unique_name("UAV")
            model = UAV(name, mesh, [0, 0, 0], [0, 0, 0])

            if mesh:
                model.display_list = create_display_list(mesh)

        elif model_type == "Obstacle":
            mesh = self.mesh_plane
            name = self.generate_unique_name("Plane")
            model = Obstacle(name, mesh, [0, 0, 0], [0, 0, 0])

            if mesh:
                model.display_list = create_display_list(mesh)

        elif model_type == "Cylinder":
            name = self.generate_unique_name("Cylinder")
            model = CylinderModel(name, position=[0, 0, 0], radius=20, height=80)

        elif model_type == "Sphere":
            name = self.generate_unique_name("Sphere")
            model = SphereModel(name, position=[0, 0, 0], diameter=40)

        else:
            print("[Scene3D] ❌ Unknown model type:", model_type)
            return None

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

        self.apply_model_altitudes()

        for obj in self.objects:
            if isinstance(obj, UAV):
                min_alt = self.get_local_min_altitude_for(obj)
                if obj.altitude < min_alt:
                    QMessageBox.warning(
                        self,
                        "Помилка",
                        f"Модель {obj.name} знаходиться нижче мінімальної висоти району {min_alt:.1f} м!"
                    )
                    return

        self.is_simulating = True
        self.timer.start(50)
        print("[Simulation] ▶ Запущено")

    def pause_simulation(self):
        self.is_simulating = False
        self.timer.stop()
        print("[Simulation] ⏸ Пауза")

    def resume_simulation(self):
        self.is_simulating = True
        self.timer.start(50)
        print("[Simulation] ▶ Simulation resumed")

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
        self.update()


    def can_start_simulation(self):
        """Перевірка, чи всі об’єкти мають speed і altitude"""
        for obj in self.objects:
            if isinstance(obj, (CylinderModel, SphereModel)):
                continue
            if obj.speed <= 0 or obj.altitude <= 0:
                return False
        return True
    
    def handle_warning_zone(self, uav, obstacles):
        def _normalize(v):
            norm = math.sqrt(sum(c*c for c in v))
            return [c / norm if norm > 0 else 0.0 for c in v]

        base_forward = [0, 0, 1]
        max_iter = 20

        candidate_moves = [
            {"name": "Підйом", "direction": [0, 1, 0], "base_vector": base_forward.copy()},
            {"name": "Спуск", "direction": [0, -1, 0], "base_vector": base_forward.copy()},
            {"name": "Вліво", "direction": [-1, 0, 0], "base_vector": base_forward.copy()},
            {"name": "Вправо", "direction": [1, 0, 0], "base_vector": base_forward.copy()},
        ]

        evaluated = []

        for move in candidate_moves:
            temp_uav = copy.deepcopy(uav)
            step = 1.0
            for i in range(max_iter):
                temp_uav.altitude += move["direction"][1] * step
                temp_uav.move_vector = [b + move["direction"][0] * step for b in move["base_vector"]]
                temp_uav.move_vector = _normalize(temp_uav.move_vector)

                risk = compute_collaborative_risk(
                    temp_uav, obstacles, self.ml_system,
                    gamma=2.0, min_altitude=self.get_local_min_altitude_for(temp_uav)
                )

                if risk < 0.3:
                    evaluated.append({
                        "name": move["name"],
                        "altitude": temp_uav.altitude,
                        "move_vector": temp_uav.move_vector,
                        "risk": round(risk, 3)
                    })
                    break
            else:
                evaluated.append({
                    "name": move["name"],
                    "altitude": temp_uav.altitude,
                    "move_vector": temp_uav.move_vector,
                    "risk": round(risk, 3)
                })

        return evaluated


    def handle_danger_zone(self, uav, obstacles):
        """
        Обирає безпечний маневр для UAV, з пріоритетом на збільшення вертикального розриву.
        Якщо існують кандидати, які для ВСІХ перешкод збільшують |vert_diff| -> вибираємо лише серед них.
        Інакше застосовуємо звичайну оцінку, але з жорсткою пеналізацією за зменшення вертикального розриву.
        Замість миттєвої зміни висоти задаємо uav.target_altitude (плавне наближення робиться в move_model).
        """
        def _normalize(v):
            norm = math.sqrt(sum(c * c for c in v))
            return [c / norm if norm > 0 else 0.0 for c in v]

        base_forward = [0, 0, 1]
        side_mag = 0.8

        candidate_moves = [
            {"name": "Підйом", "altitude": uav.altitude + 5, "move_vector": base_forward.copy()},
            {"name": "Спуск", "altitude": max(self.get_local_min_altitude_for(uav), uav.altitude - 5), "move_vector": base_forward.copy()},
            {"name": "Вліво", "altitude": uav.altitude, "move_vector": [-side_mag, 0, 1]},
            {"name": "Вправо", "altitude": uav.altitude, "move_vector": [side_mag, 0, 1]},
        ]
        for move in candidate_moves:
            move["move_vector"] = _normalize(move["move_vector"])

        moves_increase_separation = []
        orig_vert_diffs = [uav.altitude - obs.altitude for obs in obstacles] if obstacles else [0.0]

        for move in candidate_moves:
            increases_all = True
            worst_delta = None
            for obs_idx, obs in enumerate(obstacles):
                orig = orig_vert_diffs[obs_idx]
                new = move["altitude"] - obs.altitude
                delta = abs(new) - abs(orig)
                if worst_delta is None or delta < worst_delta:
                    worst_delta = delta
                if delta <= 0.0:
                    increases_all = False
            if increases_all:
                moves_increase_separation.append(move)

        eval_moves = moves_increase_separation if moves_increase_separation else candidate_moves

        payoff_matrix = np.zeros((len(eval_moves), len(obstacles)))
        lookahead_s = 5.0

        for i, move in enumerate(eval_moves):
            temp_uav = copy.deepcopy(uav)
            temp_uav.altitude = move["altitude"]
            temp_uav.move_vector = move["move_vector"]

            mv_norm = _normalize(temp_uav.move_vector)
            speed_ms = max(temp_uav.speed / 3.6, 0.1)
            dx = mv_norm[0] * speed_ms * lookahead_s
            dz = mv_norm[2] * speed_ms * lookahead_s

            total_risk = 0.0
            total_vert_penalty = 0.0
            for j, obs in enumerate(obstacles):
                proj_pos = [temp_uav.position[0] + dx, temp_uav.position[1], temp_uav.position[2] + dz]
                hor_dist = compute_distance([proj_pos[0], 0, proj_pos[2]], [obs.position[0], 0, obs.position[2]])
                new_vert = temp_uav.altitude - obs.altitude
                orig_vert = uav.altitude - obs.altitude

                risk = compute_collaborative_risk(uav, obstacles, self.ml_system, gamma=2.0, min_altitude=self.get_local_min_altitude_for(uav))

                vert_delta = abs(new_vert) - abs(orig_vert)
                if vert_delta < 0:
                    total_vert_penalty += (-vert_delta)

                vert_change_toward_obs = max(0.0, abs(orig_vert) - abs(new_vert))
                risk += vert_change_toward_obs * 0.08
                if new_vert > 10.0:
                    risk -= 0.03

                risk += 1.0 / (hor_dist + 0.1)
                if temp_uav.altitude <= self.get_local_min_altitude_for(uav) + self.min_altitude_margin:
                    risk += 1.0
                if temp_uav.altitude - uav.altitude > 15:
                    risk += 0.1

                total_risk += risk

            if not moves_increase_separation:
                total_risk += total_vert_penalty * 5.0

            payoff_matrix[i, :] = total_risk
            self.log_func(f"[DEBUG] Eval Move '{move['name']}' -> alt={move['altitude']}, total_risk={total_risk:.3f}, vert_penalty={total_vert_penalty:.3f}")

        if len(eval_moves) == 0:
            chosen_move = candidate_moves[0]
        else:
            current_risk = compute_collaborative_risk(uav, obstacles, self.ml_system, gamma=2.0, min_altitude=self.get_local_min_altitude_for(uav))
            self.log_func(f"[DEBUG] Current risk: {current_risk:.3f}")
            decision_index, strategy = hybrid_decision(payoff_matrix, current_risk)
            chosen_move = eval_moves[int(decision_index)]

        uav.target_altitude = max(self.get_local_min_altitude_for(uav), chosen_move["altitude"])
        uav.move_vector = _normalize(chosen_move["move_vector"])
        uav._maneuver_hold_ticks = int(1.0 / (self.timer.interval() / 1000.0))
        self.log_func(f"[MANEUVER] Selected '{chosen_move['name']}' alt_target={uav.target_altitude}, vec={uav.move_vector}, strategy={strategy if 'strategy' in locals() else 'N/A'}")


    def update_simulation_step(self):
        if self.ml_system is None:
            print("[STEP] ❌ ML System не передана — вихід")
            return

        uav = next((o for o in self.objects if isinstance(o, UAV)), None)
        obstacles = [o for o in self.objects if isinstance(o, Obstacle)]
        if not uav:
            print("[STEP] ❌ UAV не знайдено — вихід")
            return

        risk = compute_collaborative_risk(uav, obstacles, self.ml_system,
                                        gamma=2.0, min_altitude=self.get_local_min_altitude_for(uav))
        self.log_func(f"[STEP] Risk={risk:.3f}")
        print(f"[STEP] Risk={risk:.3f}")

        if hasattr(uav, "_maneuver_in_progress") and uav._maneuver_in_progress:
            for obj in self.objects:
                self.move_model(obj)
            self.update()
            current_risk = compute_collaborative_risk(uav, obstacles, self.ml_system,
                                                    gamma=2.0, min_altitude=self.get_local_min_altitude_for(uav))
            if current_risk < 0.3 or current_risk >= 0.7:
                uav._maneuver_in_progress = False
            return

        if risk < 0.3:
            print(f"[STEP Low] Risk={risk:.3f}")
            for obj in self.objects:
                self.move_model(obj)
            self.update()
            return

        elif risk < 0.7:
            self.pause_simulation()

            evaluated = self.handle_warning_zone(uav, obstacles)

            options = [f"{m['name']} (ризик {int(m['risk']*100)}%)" for m in evaluated]

            choice, ok = QInputDialog.getItem(
                self,
                "Жовта зона",
                "Оберіть маневр:",
                options,
                0,
                False
            )

            if ok:
                idx = options.index(choice)
                move = evaluated[idx]

                uav.target_altitude = move["altitude"]
                uav.move_vector = move["move_vector"]
                uav._maneuver_in_progress = True
                self.resume_simulation()

        else:
            print(f"[STEP Danger] Risk={risk:.3f}")
            if hasattr(uav, "_maneuver_hold_ticks") and uav._maneuver_hold_ticks > 0:
                uav._maneuver_hold_ticks -= 1
            else:
                self.handle_danger_zone(uav, obstacles)

        for obj in self.objects:
            if isinstance(obj, (UAV, Obstacle)):
                self.move_model(obj)

        self.update()

    def get_movement_vector(self, obj):
        yaw_rad = math.radians(-obj.rotation[1])
        lx, ly, lz = obj.move_vector

        fx = math.cos(yaw_rad) * lx - math.sin(yaw_rad) * lz
        fz = math.sin(yaw_rad) * lx + math.cos(yaw_rad) * lz
        fy = ly
        return [fx, fy, fz]


    def move_model(self, obj):
        """
        Рух моделі по x/z згідно move_vector, і поступова корекція висоти до obj.target_altitude.
        Максимальна зміна висоти за тик — max_alt_change_per_tick (м).
        """
        speed_ms = (obj.speed / 3.6) * 0.05 * self.sim_speed
        fx, fy, fz = self.get_movement_vector(obj)
        obj.position[0] += fx * speed_ms
        obj.position[2] += fz * speed_ms

        if not hasattr(obj, "target_altitude"):
            obj.target_altitude = getattr(obj, "altitude", obj.position[1])

        target = max(obj.target_altitude, self.get_local_min_altitude_for(obj))

        max_alt_change_per_tick = 1.0
        diff = target - obj.altitude
        if abs(diff) <= 1e-6:
            change = 0.0
        else:
            change = math.copysign(min(abs(diff), max_alt_change_per_tick), diff)
        new_alt = obj.altitude + change

        obj.altitude = new_alt
        obj.position[1] = max(new_alt, self.get_local_min_altitude_for(obj))

    def apply_model_altitudes(self):
        """Оновлює висоту моделей відповідно до параметрів altitude і ініціалізує target_altitude."""
        for obj in self.objects:
            obj.position[1] = obj.altitude
            obj.target_altitude = obj.altitude
        self.update()

    def on_district_heights_updated(self, mapping: dict):
        self.update()
        if callable(getattr(self, "log", None)):
            self.log(f"[Scene3D] Оновлено мін. висоти районів ({len(mapping)} записів)")

    def check_min_altitude_for_object(self, obj):
        x = obj.position[0]
        z = obj.position[2]
        required_min = self.kyiv_map_layer.get_min_altitude(x, z)
        return required_min

    def get_local_min_altitude_for(self, obj: BaseModel3D):
        """
        Возвращает минимальную высоту района под объектом.
        Добавляет небольшой запас min_altitude_margin.
        """
        district_min = self.kyiv_map.get_min_altitude(obj.position[0], obj.position[2])
        return district_min + self.min_altitude_margin

