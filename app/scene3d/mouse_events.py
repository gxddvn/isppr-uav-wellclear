from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent

class SceneMouseHandler:
    """
    Міксін: обробка подій миші для 3D-сцени.
    Реалізовано просте перетягування по X/Z і обертання через Shift+ЛКМ.
    """

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        mx, my = pos.x(), pos.y()
        self.last_mouse_pos = pos

        # ЛКМ
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()

            # === Shift + ЛКМ → обертання моделі ===
            if modifiers & Qt.KeyboardModifier.ShiftModifier and self.selected:
                self.is_rotating_model = True
                return

            # === Перетягування по площині X/Z ===
            if self.selected:
                self.is_dragging_model = True
                self.drag_start_pos = (mx, my)
                self.start_model_pos = list(getattr(self, f"{self.selected}_pos"))
                return

        # Середня або права кнопка — обертання камери
        elif event.button() in [Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton]:
            self.is_rotating_camera = True

    # -------------------------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent):
        cur = event.position()
        mx, my = cur.x(), cur.y()

        # === Перетягування моделі по X/Z ===
        if getattr(self, "is_dragging_model", False) and self.selected:
            dx = mx - self.drag_start_pos[0]
            dz = my - self.drag_start_pos[1]  # використовуємо Y миші для Z сцени

            factor = 0.5  # підбираємо масштаб з пікселів у координати сцени

            pos = list(getattr(self, f"{self.selected}_pos"))
            pos[0] = self.start_model_pos[0] - dx * factor
            pos[2] = self.start_model_pos[2] - dz * factor
            pos[1] = 0  # завжди на землі

            setattr(self, f"{self.selected}_pos", pos)
            self.update()
            self.last_mouse_pos = cur
            return

        # === Обертання моделі через Shift+ЛКМ ===
        if getattr(self, "is_rotating_model", False) and self.selected:
            dx = cur.x() - self.last_mouse_pos.x()
            yaw_delta = dx * 0.5 * getattr(self, "rotate_sensitivity", 1.0)

            if self.selected == "uav":
                self.uav_yaw += yaw_delta
            elif self.selected == "plane":
                self.plane_yaw += yaw_delta

            self.update()
            self.last_mouse_pos = cur
            return

        # === Обертання камери ===
        if getattr(self, "is_rotating_camera", False):
            dx = cur.x() - self.last_mouse_pos.x()
            dy = cur.y() - self.last_mouse_pos.y()
            self.camera_yaw += dx * 0.5 * getattr(self, "rotate_sensitivity", 1.0)
            self.camera_pitch -= dy * 0.5 * getattr(self, "rotate_sensitivity", 1.0)
            self.camera_pitch = max(-89, min(89, self.camera_pitch))
            self.update()
            self.last_mouse_pos = cur

    # -------------------------------------------------------------------------

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() in [
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.RightButton,
        ]:
            self.is_dragging_model = False
            self.is_rotating_model = False
            self.is_rotating_camera = False

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120
        zoom_factor = 0.9 if delta > 0 else 1.1

        # масштабування камери
        self.camera_distance *= zoom_factor ** getattr(self, "pan_sensitivity", 1.0)
        self.camera_distance = max(20.0, min(5000.0, self.camera_distance))
        print(f"[Zoom] camera_distance = {self.camera_distance:.2f}")
        self.update()
