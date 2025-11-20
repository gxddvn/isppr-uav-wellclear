from .base_model import BaseModel3D
from OpenGL.GL import *
from .draw_utils import draw_ring, draw_outline, draw_axis_gizmo

class UAV(BaseModel3D):
    def __init__(self, name, mesh, position=[0.0, 0.0, 0.0], rotation=[0, 0, 0], speed=0.0, altitude=0.0, scale=0.2, move_vector=(0,0,1)):
        super().__init__(name, mesh, position, rotation, speed, altitude, scale, move_vector)
        self.type = "UAV"
        self.safe_zones = {
            "red": 150,
            "yellow": 450,
            "green": 1450,
        }

    def draw(self, selected=False):
        glPushMatrix()
        glTranslatef(*self.position)
        glRotatef(self.rotation[1], 0, 1, 0)
        glScalef(self.scale, self.scale, self.scale)

        # малюємо модель
        if self.display_list:
            glCallList(self.display_list)

        # малюємо safe zones
        visual_scale = self.scale + 0.5
        colors = {"green": (0, 1, 0), "yellow": (1, 1, 0), "red": (1, 0, 0)}
        prev_radius = 0
        for name, radius in self.safe_zones.items():
            draw_ring(
                position=(0, 0, 0),  # в локальному просторі моделі
                inner_radius=prev_radius * visual_scale,
                outer_radius=radius * visual_scale,
                color=colors[name],
                alpha=0.25
            )
            prev_radius = radius

        # --- Підсвічування вибраного ---
        if selected:
            draw_outline(self.display_list)
            draw_axis_gizmo()

        glPopMatrix()

