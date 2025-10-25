from OpenGL.GL import *
from .draw_utils import draw_outline, draw_axis_gizmo, draw_trajectory

class BaseModel3D:
    def __init__(self, name, mesh, position, rotation, scale=1.0, forward_vector=(0,0,1)):
        self.name = name
        self.mesh = mesh
        self.position = position
        self.rotation = rotation
        self.scale = scale
        self.display_list = None  # для OpenGL display list
        self.forward_vector = forward_vector

    def draw(self, selected=False):
        """Малювання моделі та її обгортки, якщо selected=True"""
        glPushMatrix()
        glTranslatef(*self.position)
        glRotatef(self.rotation[1], 0, 1, 0)
        glScalef(self.scale, self.scale, self.scale)

        if self.mesh and self.display_list:
            glCallList(self.display_list)

        # --- Підсвічування вибраного об’єкта ---
        if selected:
            draw_outline(self.display_list)
            draw_axis_gizmo()

        glPopMatrix()

    def draw_trajectory(self):
        draw_trajectory(
            self.position,
            self.rotation[1],
            (0.2, 1.0, 0.2),
            forward_vector=self.forward_vector,
            width=4.0
        )
