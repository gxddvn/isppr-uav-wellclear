import json
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtGui import QImage
from PyQt6.QtOpenGL import QOpenGLTexture


class KyivMapLayer:
    """
    Шар карти Києва:
    - Текстура карти
    - Райони з GeoJSON
    - Точне екструдування полігонів
    - Підтримка дзеркалювання/обертання
    """

    def __init__(self, texture_path: str, geojson_path: str, bounds=None):
        self.texture_path = texture_path
        self.geojson_path = geojson_path

        if bounds:
            self.west, self.south, self.east, self.north = bounds
        else:
            self.west = 30.35
            self.east = 30.80
            self.south = 50.30
            self.north = 50.60

        self.base_lon = (self.west + self.east) / 2
        self.base_lat = (self.south + self.north) / 2

        self.scale = 1000.0

        self.texture = None
        self.districts = []

        self._load_geojson()

        self.district_colors = [
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 1, 0),
            (1, 0, 1),
            (0, 1, 1),
            (0.8, 0.4, 0),
            (0.5, 0, 0.5),
            (0.3, 0.7, 0.3),
            (0.9, 0.5, 0.2)
        ]

    # ------------------------------------------------------
    # LOAD TEXTURE
    # ------------------------------------------------------
    def load_texture_qt(self):
        try:
            img = QImage(self.texture_path).mirrored(True, True)
            if img.isNull():
                print("[KyivMap] ❌ QImage failed to load texture")
                return

            self.texture = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
            self.texture.setData(img)
            self.texture.setMinificationFilter(QOpenGLTexture.Filter.Linear)
            self.texture.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
            self.texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)

            print("[KyivMap] ✔ Texture loaded via QOpenGLTexture")
        except Exception as e:
            print("[KyivMap] ❌ Texture load failed:", e)

    # ------------------------------------------------------
    # LOAD GEOJSON
    # ------------------------------------------------------
    def _load_geojson(self):
        try:
            with open(self.geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for feature in data["features"]:
                name = feature["properties"].get("name", "unknown")
                min_alt = feature["properties"].get("min_altitude", 50)
                geom = feature["geometry"]
                polys = []

                if geom["type"] == "Polygon":
                    for ring in geom["coordinates"]:
                        polys.append(self._convert_polygon(ring))

                elif geom["type"] == "MultiPolygon":
                    for mp in geom["coordinates"]:
                        for ring in mp:
                            polys.append(self._convert_polygon(ring))

                self.districts.append({
                    "name": name,
                    "min_altitude": min_alt,
                    "polygons": polys
                })

            print("[KyivMap] ✔ GeoJSON loaded:", len(self.districts), "districts")
        except Exception as e:
            print("[KyivMap] ❌ Failed to load GeoJSON:", e)

    # ------------------------------------------------------
    # CONVERT LAT/LON → SCENE X/Z
    # ------------------------------------------------------
    def _convert_polygon(self, poly):
        out = []
        for lon, lat in poly:
            nx = (lon - self.west) / (self.east - self.west)
            nz = (lat - self.south) / (self.north - self.south)

            x = (nx - 0.5) * self.scale * 2
            z = (nz - 0.5) * self.scale * 2
            out.append((x, z))
        return out

    # ------------------------------------------------------
    # DRAW MAP
    # ------------------------------------------------------
    def draw(self):
        if not self.texture:
            return

        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        self.texture.bind()

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex3f(-self.scale, 0, -self.scale)
        glTexCoord2f(1, 0); glVertex3f(self.scale, 0, -self.scale)
        glTexCoord2f(1, 1); glVertex3f(self.scale, 0, self.scale)
        glTexCoord2f(0, 1); glVertex3f(-self.scale, 0, self.scale)
        glEnd()

        self.texture.release()
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)

        self._draw_district_borders()

    # ------------------------------------------------------
    # DRAW BORDERS
    # ------------------------------------------------------
    def _draw_district_borders(self):
        glDisable(GL_LIGHTING)
        glLineWidth(3.0)

        for i, dist in enumerate(self.districts):
            glColor3f(*self.district_colors[i % len(self.district_colors)])

            for poly in dist["polygons"]:
                mirrored = self.mirror_polygon_x(poly)

                glBegin(GL_LINE_LOOP)
                for x, z in mirrored:
                    glVertex3f(x, 0.1, z)
                glEnd()

        glLineWidth(1.0)
        glEnable(GL_LIGHTING)

    # ------------------------------------------------------
    # TESSELLATION (GLU)
    # ------------------------------------------------------
    def tessellate_polygon(self, poly, y):
        tess = gluNewTess()

        def vert_callback(v):
            glVertex3f(v[0], v[1], v[2])

        def combine_callback(coords, data, weight):
            return coords

        gluTessCallback(tess, GLU_TESS_VERTEX, vert_callback)
        gluTessCallback(tess, GLU_TESS_BEGIN, glBegin)
        gluTessCallback(tess, GLU_TESS_END, glEnd)
        gluTessCallback(tess, GLU_TESS_COMBINE, combine_callback)

        gluTessBeginPolygon(tess, None)
        gluTessBeginContour(tess)

        for x, z in poly:
            v = (x, y, z)
            gluTessVertex(tess, v, v)

        gluTessEndContour(tess)
        gluTessEndPolygon(tess)
        gluDeleteTess(tess)

    # ------------------------------------------------------
    # EXTRUDED POLYGON (3D BOX)
    # ------------------------------------------------------
    def _draw_extruded_polygon(self, poly, height):
        # Top
        self.tessellate_polygon(poly, height)

        # Bottom
        self.tessellate_polygon(poly, 0)

        # Walls
        glBegin(GL_QUADS)
        for i in range(len(poly)):
            x1, z1 = poly[i]
            x2, z2 = poly[(i + 1) % len(poly)]

            glVertex3f(x1, 0, z1)
            glVertex3f(x2, 0, z2)
            glVertex3f(x2, height, z2)
            glVertex3f(x1, height, z1)
        glEnd()

    # ------------------------------------------------------
    # DRAW ALTITUDE BOXES
    # ------------------------------------------------------
    def draw_min_altitude_boxes(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for i, dist in enumerate(self.districts):
            h = dist.get("min_altitude", 0)
            if h <= 0:
                continue

            r, g, b = self.district_colors[i % len(self.district_colors)]
            glColor4f(r, g, b, 0.3)

            for poly in dist["polygons"]:
                mirrored = self.mirror_polygon_x(poly)
                self._draw_extruded_polygon(mirrored, h)

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    # ------------------------------------------------------
    # GEOMETRY HELPERS
    # ------------------------------------------------------
    def mirror_polygon_x(self, poly, center_x=0):
        return [(2 * center_x - x, z) for x, z in poly]

    def rotate_polygon(self, poly, center=(0, 0), angle_deg=0):
        angle = math.radians(angle_deg)
        cx, cz = center
        out = []
        for x, z in poly:
            dx, dz = x - cx, z - cz
            rx = dx * math.cos(angle) - dz * math.sin(angle)
            rz = dx * math.sin(angle) + dz * math.cos(angle)
            out.append((rx + cx, rz + cz))
        return out
