import math
from OpenGL.GL import *
from OpenGL.GLU import *
from .camera import project_world_to_screen


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


def pick_model_at(scene, mouse_x, mouse_y, threshold=20):
    """
    Визначаємо, яку модель клікнув користувач,
    через 2D координати на екрані.
    
    :param scene: Scene3D
    :param mouse_x: координата X кліку миші
    :param mouse_y: координата Y кліку миші
    :param threshold: радіус вибору в пікселях
    :return: (ім'я моделі, приблизний winZ) або (None, None)
    """
    candidates = []

    models = [
        ('uav', scene.uav_pos),
        ('plane', scene.plane_pos),
    ]

    for name, pos in models:
        screen = project_world_to_screen(*pos)
        if screen is None:
            continue
        screen_x, screen_y, win_z = screen

        # Y у OpenGL відліковується знизу, тому перевертаємо
        screen_y = scene.height() - screen_y

        dx = mouse_x - screen_x
        dy = mouse_y - screen_y
        dist = math.hypot(dx, dy)

        if dist <= threshold:
            candidates.append((dist, name, win_z))

    if not candidates:
        return None, None

    # Вибираємо модель з найменшою відстанню до курсора
    candidates.sort(key=lambda x: x[0])
    chosen_name = candidates[0][1]
    chosen_win_z = candidates[0][2]

    return chosen_name, chosen_win_z


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
