from OpenGL.GL import *
import math

def draw_grid(size=500, step=50):
    glDisable(GL_LIGHTING)
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_LINES)
    for i in range(-size, size + 1, step):
        glVertex3f(i, 0, -size)
        glVertex3f(i, 0, size)
        glVertex3f(-size, 0, i)
        glVertex3f(size, 0, i)
    glEnd()
    glEnable(GL_LIGHTING)


def draw_outline(display_list):
    """Малює обводку навколо моделі в локальному просторі (glPushMatrix уже застосовано)"""
    if not display_list:
        return
    glEnable(GL_BLEND)
    glColor3f(0.2, 0.5, 1.0)  # синя рамка
    glLineWidth(3.0)
    # просто викликаємо display_list як каркас або контур
    glCallList(display_list)
    glLineWidth(1.0)
    glDisable(GL_BLEND)



def draw_axis_gizmo(length=50.0):
    """Малює осі X/Y/Z у поточному локальному просторі"""
    glLineWidth(2.0)
    glBegin(GL_LINES)
    # X - червона
    glColor3f(1.0, 0.0, 0.0)
    glVertex3f(0, 0, 0)
    glVertex3f(length, 0, 0)
    # Y - зелена
    glColor3f(0.0, 1.0, 0.0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, length, 0)
    # Z - синя
    glColor3f(0.0, 0.0, 1.0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, length)
    glEnd()
    glLineWidth(1.0)



def draw_axis_arrow(pos, dir_vec, color=(1, 1, 1)):
    x, y, z = pos
    dx, dy, dz = dir_vec
    head_len = 5.0
    head_width = 2.5
    glDisable(GL_LIGHTING)
    glColor3f(*color)
    glBegin(GL_TRIANGLES)
    if dx:
        glVertex3f(x, y, z)
        glVertex3f(x - head_len, y + head_width, z + head_width)
        glVertex3f(x - head_len, y - head_width, z - head_width)
    elif dy:
        glVertex3f(x, y, z)
        glVertex3f(x + head_width, y - head_len, z + head_width)
        glVertex3f(x - head_width, y - head_len, z - head_width)
    glEnd()
    glEnable(GL_LIGHTING)


def draw_trajectory(pos, yaw, color=(1.0,1.0,1.0), length=50.0, forward_vector=(0,0,1), width=3.0):
    """
    Рисует траекторию модели от носа в направлении её forward_vector с учётом yaw.
    
    :param pos: [x, y, z] — позиция модели (центр)
    :param yaw: float — поворот модели вокруг Y (в градусах)
    :param color: RGB кортеж
    :param length: длина траектории
    :param forward_vector: локальная ось “вперед” модели (x, y, z)
    """
    x, y, z = pos
    fx, fy, fz = forward_vector

    # Преобразуем локальный forward в мировой с учётом yaw
    # yaw = вращение вокруг Y
    yaw_rad = math.radians(yaw)
    world_fx = fx * math.cos(yaw_rad) + fz * math.sin(yaw_rad)
    world_fz = -fx * math.sin(yaw_rad) + fz * math.cos(yaw_rad)
    world_fy = fy  # Y не меняется

    # Начало траектории — нос
    nose_x = x + world_fx * length
    nose_y = y + world_fy * length
    nose_z = z + world_fz * length

    # Конец линии — центр модели (или tail)
    tail_x = x
    tail_y = y
    tail_z = z

    glColor3f(*color)
    glLineWidth(width)
    glBegin(GL_LINES)
    glVertex3f(nose_x, nose_y, nose_z)
    glVertex3f(tail_x, tail_y, tail_z)
    glEnd()
    glLineWidth(1.0)


def create_display_list(mesh):
    list_id = glGenLists(1)
    glNewList(list_id, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    for face in mesh.faces:
        for idx in face:
            glVertex3f(*mesh.vertices[idx])
    glEnd()
    glEndList()
    return list_id

def draw_ring(position, outer_radius=100.0, inner_radius=None, color=(0.2, 0.8, 0.2), alpha=0.3, segments=64):
    if inner_radius is None:
        inner_radius = outer_radius * 0.85

    glPushMatrix()
    glTranslatef(*position)

    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(*color, alpha)

    glBegin(GL_TRIANGLE_STRIP)
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        glVertex3f(inner_radius * cos_a, 0.03, inner_radius * sin_a)
        glVertex3f(outer_radius * cos_a, 0.03, outer_radius * sin_a)
    glEnd()

    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)
    glPopMatrix()

def draw_cube(self, size=1.0):
    hs = size / 2.0  # половина розміру
    glBegin(GL_QUADS)

    # front
    glVertex3f(-hs, -hs, hs)
    glVertex3f(hs, -hs, hs)
    glVertex3f(hs, hs, hs)
    glVertex3f(-hs, hs, hs)
    # back
    glVertex3f(-hs, -hs, -hs)
    glVertex3f(-hs, hs, -hs)
    glVertex3f(hs, hs, -hs)
    glVertex3f(hs, -hs, -hs)
    # left
    glVertex3f(-hs, -hs, -hs)
    glVertex3f(-hs, -hs, hs)
    glVertex3f(-hs, hs, hs)
    glVertex3f(-hs, hs, -hs)
    # right
    glVertex3f(hs, -hs, -hs)
    glVertex3f(hs, hs, -hs)
    glVertex3f(hs, hs, hs)
    glVertex3f(hs, -hs, hs)
    # top
    glVertex3f(-hs, hs, -hs)
    glVertex3f(-hs, hs, hs)
    glVertex3f(hs, hs, hs)
    glVertex3f(hs, hs, -hs)
    # bottom
    glVertex3f(-hs, -hs, -hs)
    glVertex3f(hs, -hs, -hs)
    glVertex3f(hs, -hs, hs)
    glVertex3f(-hs, -hs, hs)

    glEnd()

