from OpenGL.GL import *
from OpenGL.GLU import *
from .base_model import BaseModel3D
import math

class StaticObstacle:
    def __init__(self, position=(0, 0, 0)):
        self.position = position  # x, y, z
        self.color = (0.5, 0.5, 0.5)

    def draw(self):
        pass

    def set_color(self, color):
        self.color = color


class CylinderModel(BaseModel3D):
    def __init__(self, name, position=(0,0,0), radius=10, height=50):
        super().__init__(name, None, position, [0, 0, 0])
        self.radius = radius
        self.height = height
        self.color = (1.0, 1.0, 0.0)

    def draw(self, selected=False):
        glPushMatrix()
        glTranslatef(*self.position)

        if selected:
            glColor3f(1.0, 0.6, 0.0)
        else:
            glColor3f(*self.color)

        glRotatef(-90, 1, 0, 0)

        quad = gluNewQuadric()
        gluCylinder(quad, self.radius, self.radius, self.height, 32, 1)

        glPushMatrix()
        glTranslatef(0, 0, self.height)
        gluDisk(quad, 0, self.radius, 32, 1)
        glPopMatrix()

        gluDisk(quad, 0, self.radius, 32, 1)

        gluDeleteQuadric(quad)
        glPopMatrix()

class SphereModel(BaseModel3D):
    def __init__(self, name, position=(0,0,0), diameter=20):
        super().__init__(name, None, position, [0, 0, 0])
        self.diameter = diameter
        self.color = (0.6, 0.0, 0.8)

    def draw(self, selected=False):
        glPushMatrix()
        glTranslatef(*self.position)
        glColor3f(*self.color)
        gluSphere(gluNewQuadric(), self.diameter/2, 32, 32)
        glPopMatrix()
