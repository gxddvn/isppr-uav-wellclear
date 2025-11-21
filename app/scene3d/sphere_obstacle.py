from .static_obstacle import StaticObstacle

class SphereObstacle(StaticObstacle):
    def __init__(self, position=(0,0,0), diameter=2):
        super().__init__(position)
        self.diameter = diameter
        self.color = (0.6, 0.0, 0.8)

    def draw(self):
        print(f"Draw sphere at {self.position} with d={self.diameter}, color=Purple")
