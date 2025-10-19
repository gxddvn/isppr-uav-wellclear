import math
from OpenGL.GL import *
from OpenGL.GLU import *


def project_world_to_screen(x, y, z):
    model = glGetDoublev(GL_MODELVIEW_MATRIX)
    proj = glGetDoublev(GL_PROJECTION_MATRIX)
    view = glGetIntegerv(GL_VIEWPORT)
    return gluProject(x, y, z, model, proj, view)


def unproject_screen_to_world(winx, winy, winz):
    model = glGetDoublev(GL_MODELVIEW_MATRIX)
    proj = glGetDoublev(GL_PROJECTION_MATRIX)
    view = glGetIntegerv(GL_VIEWPORT)
    return gluUnProject(winx, winy, winz, model, proj, view)


def pick_model_at(scene, mouse_x, mouse_y):
    """Ray pick — визначає, у яку модель клікнув користувач."""
    h = scene.height()
    ogl_y = h - mouse_y

    start = unproject_screen_to_world(mouse_x, ogl_y, 0.0)
    end = unproject_screen_to_world(mouse_x, ogl_y, 1.0)
    if not start or not end:
        return None, None

    ox, oy, oz = start
    ex, ey, ez = end

    # 🔁 напрямок має бути в сторону камери
    dx, dy, dz = (ox - ex, oy - ey, oz - ez)

    def ray_sphere_t(ray_o, ray_d, center, radius):
        ox, oy, oz = ray_o
        dx, dy, dz = ray_d
        cx, cy, cz = center
        a = dx*dx + dy*dy + dz*dz
        b = 2 * (dx*(ox-cx) + dy*(oy-cy) + dz*(oz-cz))
        c = (ox-cx)**2 + (oy-cy)**2 + (oz-cz)**2 - radius*radius
        disc = b*b - 4*a*c
        if disc < 0:
            return None
        sqrt_d = math.sqrt(disc)
        t1 = (-b - sqrt_d) / (2*a)
        t2 = (-b + sqrt_d) / (2*a)
        ts = [t for t in (t1, t2) if t > 1e-6]
        if not ts:
            return None
        return min(ts)

    spheres = [
        ('uav', tuple(scene.uav_pos), 25.0),
        ('plane', tuple(scene.plane_pos), 35.0),
    ]

    hits = []
    for name, center, radius in spheres:
        t = ray_sphere_t((ox, oy, oz), (dx, dy, dz), center, radius)
        if t is not None:
            hits.append((t, name))

    if not hits:
        return None, None

    hits.sort(key=lambda x: x[0])
    chosen_name = hits[0][1]

    return chosen_name, 0.5


def cursor_on_gizmo(scene, mouse_x, mouse_y):
    """Перевіряє, чи курсор знаходиться поруч з Gizmo (ось X або Y)."""
    if not scene.selected:
        return False

    pos = getattr(scene, f"{scene.selected}_pos")
    x, y, z = pos
    size = 40.0

    axis_endpoints = {
        'x': (x + size, y, z),
        'y': (x, y + size, z),
    }

    screen_points = {}
    for axis, end in axis_endpoints.items():
        sx1, sy1, _ = project_world_to_screen(x, y, z)
        sx2, sy2, _ = project_world_to_screen(*end)
        screen_points[axis] = ((sx1, sy1), (sx2, sy2))

    threshold = 10.0

    def point_to_segment_distance(px, py, x1, y1, x2, y2):
        vx, vy = x2 - x1, y2 - y1
        wx, wy = px - x1, py - y1
        c1 = vx * wx + vy * wy
        if c1 <= 0:
            return math.hypot(px - x1, py - y1)
        c2 = vx * vx + vy * vy
        if c2 <= c1:
            return math.hypot(px - x2, py - y2)
        b = c1 / c2
        bx, by = x1 + b * vx, y1 + b * vy
        return math.hypot(px - bx, py - by)

    hit_axis = None
    min_dist = float('inf')
    for axis, ((x1, y1), (x2, y2)) in screen_points.items():
        dist = point_to_segment_distance(mouse_x, scene.height() - mouse_y, x1, y1, x2, y2)
        if dist < threshold and dist < min_dist:
            hit_axis = axis
            min_dist = dist

    if hit_axis:
        scene._last_gizmo_axis = hit_axis
        return True

    scene._last_gizmo_axis = None
    return False


def detect_gizmo_axis(scene):
    """Повертає вектор осей (1,0,0) або (0,1,0) залежно від натиснутої осі."""
    if hasattr(scene, "_last_gizmo_axis") and scene._last_gizmo_axis:
        if scene._last_gizmo_axis == 'x':
            return (1, 0, 0)
        elif scene._last_gizmo_axis == 'y':
            return (0, 1, 0)
    return (0, 0, 0)
