from .base_model import BaseModel3D

class Obstacle(BaseModel3D):
    def __init__(self, name, mesh, position, rotation, scale=1.0, forward_vector=(-1,0,0)):
        super().__init__(name, mesh, position, rotation, scale, forward_vector)
