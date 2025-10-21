import math
from OpenGL.GL import *
from OpenGL.GLU import *

def apply_camera(scene):
    ex = scene.camera_distance * math.cos(math.radians(scene.camera_pitch)) * math.sin(math.radians(scene.camera_yaw))
    ey = scene.camera_distance * math.sin(math.radians(scene.camera_pitch))
    ez = scene.camera_distance * math.cos(math.radians(scene.camera_pitch)) * math.cos(math.radians(scene.camera_yaw))
    glLoadIdentity()
    _glu_look_at(ex, ey, ez, 0, 0, 0, 0, 1, 0)

def paintGL(self):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    apply_camera(self)

    # 🔥 зберігаємо поточні матриці камери
    self._modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
    self._projection = glGetDoublev(GL_PROJECTION_MATRIX)
    self._viewport = glGetIntegerv(GL_VIEWPORT)

def set_projection(w, h):
    from OpenGL.GL import glMatrixMode, glLoadIdentity, glFrustum, GL_PROJECTION, GL_MODELVIEW
    aspect = w / max(h, 1)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    _glu_perspective(45.0, aspect, 1.0, 5000.0)
    glMatrixMode(GL_MODELVIEW)

def _glu_perspective(fovY, aspect, zNear, zFar):
    fH = math.tan(fovY / 360.0 * math.pi) * zNear
    fW = fH * aspect
    glFrustum(-fW, fW, -fH, fH, zNear, zFar)

def _glu_look_at(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, upX, upY, upZ):
    f = [centerX - eyeX, centerY - eyeY, centerZ - eyeZ]
    flen = math.sqrt(sum(i*i for i in f))
    f = [i / flen for i in f]
    up = [upX, upY, upZ]
    up_len = math.sqrt(sum(i*i for i in up))
    up = [i / up_len for i in up]
    s = [
        f[1]*up[2] - f[2]*up[1],
        f[2]*up[0] - f[0]*up[2],
        f[0]*up[1] - f[1]*up[0]
    ]
    s_len = math.sqrt(sum(i*i for i in s))
    s = [i / s_len for i in s]
    u = [
        s[1]*f[2] - s[2]*f[1],
        s[2]*f[0] - s[0]*f[2],
        s[0]*f[1] - s[1]*f[0]
    ]
    m = [
        [s[0], u[0], -f[0], 0],
        [s[1], u[1], -f[1], 0],
        [s[2], u[2], -f[2], 0],
        [0, 0, 0, 1]
    ]
    from OpenGL.GL import glMultMatrixf, glTranslatef
    glMultMatrixf([m[j][i] for i in range(4) for j in range(4)])
    glTranslatef(-eyeX, -eyeY, -eyeZ)

def project_world_to_screen(x, y, z):
    model = glGetDoublev(GL_MODELVIEW_MATRIX)
    proj = glGetDoublev(GL_PROJECTION_MATRIX)
    view = glGetIntegerv(GL_VIEWPORT)
    return gluProject(x, y, z, model, proj, view)
