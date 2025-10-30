from .base_model import BaseModel3D

class Obstacle(BaseModel3D):
    def __init__(self, name, mesh, position=[0.0, 0.0, 0.0], rotation=[0, 0, 0], speed=0.0, altitude=0.0, scale=1.0, move_vector=(-1,0,0)):
        super().__init__(name, mesh, position, rotation, speed, altitude, scale, move_vector)
