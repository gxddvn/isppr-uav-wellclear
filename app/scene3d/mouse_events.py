from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QWheelEvent

class SceneMouseHandler:
    """
    Міксін: реалізує події миші, клавіатури та колеса.
    """
    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position()
        mx, my = pos.x(), pos.y()
        self.last_mouse_pos = pos

        from .picking import pick_model_at, cursor_on_gizmo, detect_gizmo_axis

        # ЛКМ
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()

            # Shift + ЛКМ = обертання виділеної моделі
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                if self.selected:
                    self.is_rotating_model = True
                return

            # Курсор на гізмо = drag моделі по осях
            if self.selected and cursor_on_gizmo(self, mx, my):
                self.is_dragging_model = True
                self.drag_win_z = 0.5
                self.drag_axis = detect_gizmo_axis(self, mx, my)
                return

            # Pick моделі, якщо дозволено
            if getattr(self, "allow_mouse_pick", True):
                name, winZ = pick_model_at(self, mx, my)
                if name:
                    self.selected = name
                    self.drag_win_z = winZ
                    self.drag_axis = (1, 1, 0)
                # не скасовувати виділення, якщо нічого не знайдено


        # Середній або ПКМ = обертання камери
        elif event.button() in [Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton]:
            self.is_rotating_camera = True


    def mouseMoveEvent(self, event: QMouseEvent):
        if self.last_mouse_pos is None:
            self.last_mouse_pos = event.position()
            return

        cur = event.position()
        dx = cur.x() - self.last_mouse_pos.x()
        dy = cur.y() - self.last_mouse_pos.y()

        # Обертання камери
        if getattr(self, "is_rotating_camera", False):
            self.camera_yaw += dx * 0.5 * self.rotate_sensitivity
            self.camera_pitch -= dy * 0.5 * self.rotate_sensitivity
            self.camera_pitch = max(-89, min(89, self.camera_pitch))
            self.update()
            self.last_mouse_pos = cur
            return

        # Drag моделі
        if getattr(self, "is_dragging_model", False) and self.drag_win_z is not None and self.drag_axis:
            mx, my = cur.x(), cur.y()
            ogl_y = self.height() - my
            wx, wy, wz = self._unproject_screen_to_world(mx, ogl_y, self.drag_win_z)
            ox, oy, oz = getattr(self, f"{self.selected}_pos")
            delta_x = wx - ox
            delta_y = wy - oy
            nx = ox + delta_x * self.drag_axis[0]
            ny = oy + delta_y * self.drag_axis[1]
            fixed_z = 10
            setattr(self, f"{self.selected}_pos", [nx, ny, fixed_z])
            self.update()

        # Обертання моделі
        if getattr(self, "is_rotating_model", False):
            if self.selected == 'uav':
                self.uav_yaw += dx * 0.5 * self.rotate_sensitivity
            elif self.selected == 'plane':
                self.plane_yaw += dx * 0.5 * self.rotate_sensitivity
            self.update()
            self.last_mouse_pos = cur
            return

        self.last_mouse_pos = cur

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton]:
            self.is_dragging_model = False
            self.is_rotating_model = False
            self.is_rotating_camera = False
            self.drag_win_z = None
            self.drag_axis = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selected = None
            self.is_dragging_model = False
            self.is_rotating_model = False
            self.drag_axis = None
            self.update()
        elif hasattr(super(), 'keyPressEvent'):
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120
        zoom_factor = 0.9 if delta > 0 else 1.1
        if delta > 0:
            self.camera_distance *= (zoom_factor ** self.pan_sensitivity)
        else:
            self.camera_distance *= (zoom_factor ** (1.0 / self.pan_sensitivity))
        self.camera_distance = max(20.0, min(5000.0, self.camera_distance))
        self.update()
