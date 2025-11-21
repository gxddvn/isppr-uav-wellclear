from .static_obstacle import StaticObstacle

class CylinderObstacle(StaticObstacle):
    def __init__(self, position=(0,0,0), radius=1, height=5):
        super().__init__(position)
        self.radius = radius
        self.height = height
        self.color = (1.0, 1.0, 0.0)

    def draw(self):
        print(f"Draw cylinder at {self.position} with r={self.radius}, h={self.height}, color=Yellow")
