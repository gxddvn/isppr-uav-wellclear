import math
from OpenGL.GL import *

def glu_perspective(fovY, aspect, zNear, zFar):
    fH = math.tan(fovY / 360.0 * math.pi) * zNear
    fW = fH * aspect
    glFrustum(-fW, fW, -fH, fH, zNear, zFar)

def glu_look_at(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, upX, upY, upZ):
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
    glMultMatrixf([m[j][i] for i in range(4) for j in range(4)])
    glTranslatef(-eyeX, -eyeY, -eyeZ)
