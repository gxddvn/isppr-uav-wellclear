import json
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtGui import QImage
from PyQt6.QtOpenGL import QOpenGLTexture


class KyivMapLayer:
    """
    Оптимізований шар карти Києва:
    - Текстура карти
    - Райони з GeoJSON
    - Точне екструдування полігонів (GLU tessellation)
    - Кешування геометрії у Display Lists для продуктивності
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

        # Display list cache
        self.district_dl = []   # list of GL list ids or None
        self.dl_valid = False   # flag, треба пересоздати DL якщо змінились висоти/геометрія

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

    # ---------------------------
    # TEXTURE
    # ---------------------------
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

    # ---------------------------
    # GEOJSON
    # ---------------------------
    def _load_geojson(self):
        try:
            with open(self.geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.districts = []
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
                    "min_altitude": float(min_alt),
                    "polygons": polys
                })

            # invalidate display lists — нова геометрія
            self.invalidate_display_lists()
            print("[KyivMap] ✔ GeoJSON loaded:", len(self.districts), "districts")
        except Exception as e:
            print("[KyivMap] ❌ Failed to load GeoJSON:", e)

    # ---------------------------
    # COORDS CONVERSION
    # ---------------------------
    def _convert_polygon(self, poly):
        out = []
        for lon, lat in poly:
            nx = (lon - self.west) / (self.east - self.west)
            nz = (lat - self.south) / (self.north - self.south)

            x = (nx - 0.5) * self.scale * 2
            z = (nz - 0.5) * self.scale * 2
            out.append((x, z))
        return out

    # ---------------------------
    # DRAW MAP (texture + borders)
    # ---------------------------
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

    # ---------------------------
    # TESSELLATION (GLU) helpers
    # ---------------------------
    def _glu_tess_begin(self, mode):
        # mode will be GL_TRIANGLES or similar
        glBegin(mode)

    def _glu_tess_end(self):
        glEnd()

    def _glu_tess_vertex(self, vertex_data):
        # vertex_data is the same object we passed to gluTessVertex (a tuple)
        glVertex3f(vertex_data[0], vertex_data[1], vertex_data[2])

    def _glu_tess_combine(self, coords, vertex_data, weight):
        # coords is a tuple of 3 floats; just return it as a new vertex
        return (coords[0], coords[1], coords[2])

    def tessellate_polygon(self, poly, y):
        """
        Виконує тесселяцію одного контуру (poly) на висоті y.
        poly: list of (x,z)
        y: height (float)
        """
        # Create tessellator
        tess = gluNewTess()

        # Register callbacks
        gluTessCallback(tess, GLU_TESS_BEGIN, self._glu_tess_begin)
        gluTessCallback(tess, GLU_TESS_END, self._glu_tess_end)
        gluTessCallback(tess, GLU_TESS_VERTEX, self._glu_tess_vertex)
        gluTessCallback(tess, GLU_TESS_COMBINE, self._glu_tess_combine)
        # Optional: error callback
        # gluTessCallback(tess, GLU_TESS_ERROR, lambda err: print("Tess error:", err))

        gluTessBeginPolygon(tess, None)
        gluTessBeginContour(tess)

        for x, z in poly:
            v = (x, y, z)
            # Note: PyOpenGL will pass this tuple back to vertex callback
            gluTessVertex(tess, v, v)

        gluTessEndContour(tess)
        gluTessEndPolygon(tess)

        gluDeleteTess(tess)

    # ---------------------------
    # EXTRUDE & DRAW (used inside display list build)
    # ---------------------------
    def _draw_extruded_polygon_immediate(self, poly, height):
        """
        Малює екструдований полігон у immediate mode.
        Використовується при побудові display list.
        """
        # Top (tessellated)
        self.tessellate_polygon(poly, height)

        # Bottom (tessellated)
        self.tessellate_polygon(poly, 0.0)

        # Walls
        glBegin(GL_QUADS)
        n = len(poly)
        for i in range(n):
            x1, z1 = poly[i]
            x2, z2 = poly[(i + 1) % n]

            glVertex3f(x1, 0.0, z1)
            glVertex3f(x2, 0.0, z2)
            glVertex3f(x2, height, z2)
            glVertex3f(x1, height, z1)
        glEnd()

    # ---------------------------
    # DISPLAY LISTS (building, invalidation)
    # ---------------------------
    def invalidate_display_lists(self):
        """Позначити, що DL не валідні та потрібно пересоздати."""
        self.dl_valid = False

    def delete_display_lists(self):
        """Видалити поточні GL списки (якщо були)."""
        for dl in self.district_dl:
            if dl:
                try:
                    glDeleteLists(dl, 1)
                except Exception:
                    pass
        self.district_dl = []
        self.dl_valid = False

    def build_altitude_display_lists(self):
        """
        Побудова/перебудова display lists для всіх районів.
        Викликати, коли змінено min_altitude або після завантаження GeoJSON.
        """
        # видаляємо старі
        self.delete_display_lists()

        self.district_dl = []
        for i, dist in enumerate(self.districts):
            h = float(dist.get("min_altitude", 0.0))
            if h <= 0 or not dist["polygons"]:
                self.district_dl.append(None)
                continue

            dl = glGenLists(1)
            glNewList(dl, GL_COMPILE)

            # Задаємо колір тут (включено alpha)
            r, g, b = self.district_colors[i % len(self.district_colors)]
            glColor4f(r, g, b, 0.3)

            # Для кожного полігона району малюємо екструзію
            for poly in dist["polygons"]:
                mirrored = self.mirror_polygon_x(poly)
                self._draw_extruded_polygon_immediate(mirrored, h)

            glEndList()
            self.district_dl.append(dl)

        self.dl_valid = True

    # ---------------------------
    # DRAW ALTITUDE BOXES (CALLLISTS)
    # ---------------------------
    def draw_min_altitude_boxes(self):
        """
        Основна функція рендеру — використовує display lists.
        """
        # Перевірити чи потрібно пересоздати DL
        if not self.dl_valid:
            self.build_altitude_display_lists()

        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Викликаємо списки
        for dl in self.district_dl:
            if dl:
                glCallList(dl)

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    # ---------------------------
    # HELPERS
    # ---------------------------
    def mirror_polygon_x(self, poly, center_x=0.0):
        return [(2 * center_x - x, z) for x, z in poly]

    def rotate_polygon(self, poly, center=(0.0, 0.0), angle_deg=0.0):
        angle = math.radians(angle_deg)
        cx, cz = center
        out = []
        for x, z in poly:
            dx, dz = x - cx, z - cz
            rx = dx * math.cos(angle) - dz * math.sin(angle)
            rz = dx * math.sin(angle) + dz * math.cos(angle)
            out.append((rx + cx, rz + cz))
        return out

    # ---------------------------
    # ALTITUDE MANAGEMENT (invalidate DL on change)
    # ---------------------------
    def set_min_altitude_for_district(self, district_index: int, min_alt: float):
        if 0 <= district_index < len(self.districts):
            self.districts[district_index]["min_altitude"] = float(min_alt)
            self.invalidate_display_lists()
            return True
        return False

    def set_min_altitude_for_district_by_name(self, name: str, min_alt: float):
        for d in self.districts:
            if d["name"] == name:
                d["min_altitude"] = float(min_alt)
                self.invalidate_display_lists()
                return True
        return False

    def get_min_altitude(self, x, z):
        d = self.find_district(x, z)
        if d:
            return float(d.get("min_altitude", 0.0))
        return 0.0

    def export_min_altitudes(self, path: str):
        out = {d["name"]: d.get("min_altitude", 0) for d in self.districts}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    def import_min_altitudes(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in self.districts:
                if d["name"] in data:
                    d["min_altitude"] = float(data[d["name"]])
            self.invalidate_display_lists()
            return True
        except Exception as e:
            print("[KyivMap] ❌ import_min_altitudes failed:", e)
            return False

    # ---------------------------
    # POINT-IN-POLYGON
    # ---------------------------
    def point_in_polygon(self, x, z, poly):
        inside = False
        n = len(poly)
        px, pz = x, z

        for i in range(n):
            x1, z1 = poly[i]
            x2, z2 = poly[(i + 1) % n]

            if ((z1 > pz) != (z2 > pz)) and \
               (px < (x2 - x1) * (pz - z1) / (z2 - z1 + 1e-9) + x1):
                inside = not inside
        return inside

    def find_district(self, x, z):
        for dist in self.districts:
            for poly in dist["polygons"]:
                if self.point_in_polygon(x, z, poly):
                    return dist
        return None

    # ---------------------------
    # CLEANUP
    # ---------------------------
    def __del__(self):
        try:
            self.delete_display_lists()
        except Exception:
            pass
