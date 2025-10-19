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


def draw_outline(list_id, pos, yaw):
    glPushAttrib(GL_ENABLE_BIT | GL_LINE_BIT | GL_POLYGON_BIT)
    glDisable(GL_LIGHTING)
    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    glLineWidth(2.5)
    glColor3f(0.1, 0.6, 1.0)
    glPushMatrix()
    glTranslatef(*pos)
    glRotatef(yaw, 0, 1, 0)
    glCallList(list_id)
    glPopMatrix()
    glPopAttrib()


def draw_axis_gizmo(pos, size=40.0):
    x, y, z = pos
    glDisable(GL_LIGHTING)
    glLineWidth(3.0)
    glBegin(GL_LINES)

    # X — червона
    glColor3f(1.0, 0.2, 0.2)
    glVertex3f(x, y, z)
    glVertex3f(x + size, y, z)

    # Y — зелена
    glColor3f(0.2, 1.0, 0.2)
    glVertex3f(x, y, z)
    glVertex3f(x, y + size, z)

    glEnd()
    glEnable(GL_LIGHTING)

    draw_axis_arrow((x + size, y, z), (1, 0, 0), (1.0, 0.2, 0.2))
    draw_axis_arrow((x, y + size, z), (0, 1, 0), (0.2, 1.0, 0.2))


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


def draw_trajectory(pos, yaw_deg, color=(1, 1, 0.2), length=80.0):
    yaw = math.radians(yaw_deg)
    dx = math.sin(yaw)
    dz = math.cos(yaw)
    sx, sy, sz = pos
    ex, ey, ez = sx + dx * length, sy, sz + dz * length
    glDisable(GL_LIGHTING)
    glLineWidth(2.0)
    glColor3f(*color)
    glBegin(GL_LINES)
    glVertex3f(sx, sy + 5.0, sz)
    glVertex3f(ex, ey + 5.0, ez)
    glEnd()
    glEnable(GL_LIGHTING)


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
