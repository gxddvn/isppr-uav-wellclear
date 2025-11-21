import math
from OpenGL.GL import *
from OpenGL.GLU import *
from .camera import project_world_to_screen


def project_world_to_screen(scene, x, y, z):
    from OpenGL.GLU import gluProject

    model = getattr(scene, "_modelview", None)
    proj = getattr(scene, "_projection", None)
    view = getattr(scene, "_viewport", None)

    if model is None or proj is None or view is None:
        from OpenGL.GL import (
            glGetDoublev, glGetIntegerv,
            GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX, GL_VIEWPORT
        )
        model = glGetDoublev(GL_MODELVIEW_MATRIX)
        proj = glGetDoublev(GL_PROJECTION_MATRIX)
        view = glGetIntegerv(GL_VIEWPORT)

    sx, sy, sz = gluProject(x, y, z, model, proj, view)
    print(f"[Proj] world=({x:.1f},{y:.1f},{z:.1f}) -> screen=({sx:.1f},{sy:.1f},{sz:.3f})")
    return sx, sy, sz




def unproject_screen_to_world(winx, winy, winz, scene=None):
    from OpenGL.GLU import gluUnProject
    from OpenGL.GL import glGetDoublev, glGetIntegerv, GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX, GL_VIEWPORT

    if scene and hasattr(scene, "_modelview"):
        model = scene._modelview
        proj = scene._projection
        view = scene._viewport
    else:
        model = glGetDoublev(GL_MODELVIEW_MATRIX)
        proj = glGetDoublev(GL_PROJECTION_MATRIX)
        view = glGetIntegerv(GL_VIEWPORT)

    wx, wy, wz = gluUnProject(winx, winy, winz, model, proj, view)
    return wx, wy, wz

def pick_model_at(scene, mouse_x, mouse_y, threshold=100):
    """
    Визначає, яку модель клікнув користувач.
    """
    candidates = []
    for obj in scene.objects:
        screen = project_world_to_screen(scene, *obj.pos)
        if screen is None:
            continue
        sx, sy, sz = screen
        sy = scene.height() - sy  # переворот Y

        dist = math.hypot(mouse_x - sx, mouse_y - sy)
        if dist <= threshold:
            candidates.append((dist, obj))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]  # повертаємо об'єкт SceneObject

def cursor_on_gizmo(scene, mouse_x, mouse_y):
    import math
    from OpenGL.GL import (
        glGetDoublev, glGetIntegerv,
        GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX, GL_VIEWPORT
    )

    if not getattr(scene, "selected", None):
        scene._last_gizmo_axis = None
        return False

    # 🧭 переконуємось, що маємо актуальні матриці
    if not hasattr(scene, "_modelview"):
        scene._modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
    if not hasattr(scene, "_projection"):
        scene._projection = glGetDoublev(GL_PROJECTION_MATRIX)
    if not hasattr(scene, "_viewport"):
        scene._viewport = glGetIntegerv(GL_VIEWPORT)

    pos = getattr(scene, f"{scene.selected}_pos")
    x, y, z = pos
    size = 100.0

    axis_endpoints = {
        "x": (x + size, y, z),
        "z": (x, y, z + size),
    }

    screen_points = {}

    # ✅ проєкція базової точки + кінців осей
    for axis, end in axis_endpoints.items():
        sx1, sy1, _ = project_world_to_screen(scene, x, y, z)
        sx2, sy2, _ = project_world_to_screen(scene, *end)

        # OpenGL -> Qt Y
        sy1 = scene.height() - sy1
        sy2 = scene.height() - sy2

        screen_points[axis] = ((sx1, sy1), (sx2, sy2))

    threshold = 100.0

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

    print(f"[GizmoCheck] mouse=({mouse_x:.0f},{mouse_y:.0f})")

    hit_axis = None
    min_dist = float("inf")

    for axis, ((x1, y1), (x2, y2)) in screen_points.items():
        dist = point_to_segment_distance(mouse_x, mouse_y, x1, y1, x2, y2)
        print(f"   axis={axis} dist={dist:.1f}")
        if dist < threshold and dist < min_dist:
            hit_axis = axis
            min_dist = dist

    print(f"→ hit_axis={hit_axis}")
    scene._last_gizmo_axis = hit_axis
    return hit_axis is not None


def detect_gizmo_axis(scene):
    """Повертає вектор осей (1,0,0) або (0,1,0) залежно від натиснутої осі."""
    if hasattr(scene, "_last_gizmo_axis") and scene._last_gizmo_axis:
        if scene._last_gizmo_axis == 'x':
            return (1,0,0)
        elif scene._last_gizmo_axis == 'z':
            return (0,0,1)
    return (0, 0, 0)
