import json
import math
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt6.QtGui import QImage
from PyQt6.QtOpenGL import QOpenGLTexture
from PIL import Image


class KyivMapLayer:
    """
    Шар карти Києва:
    - Текстура карти (satellite/OSM)
    - Райони Києва з GeoJSON
    - Полігони районів
    - Метод визначення району за координатами
    """

    def __init__(self, texture_path: str, geojson_path: str, bounds=None):
        self.texture_path = texture_path
        self.geojson_path = geojson_path

        # bounds: (west, south, east, north)
        if bounds:
            self.west, self.south, self.east, self.north = bounds
        else:
            # fallback
            self.west = 30.35
            self.east = 30.80
            self.south = 50.30
            self.north = 50.60

        # Центр карты рассчитываем автоматически
        self.base_lon = (self.west + self.east) / 2
        self.base_lat = (self.south + self.north) / 2

        self.scale = 1000.0

        self.texture_id = None
        self.districts = []

        # self.load_texture_safe()
        self._load_geojson()
        self.district_colors = [
            (1, 0, 0),       # червоний
            (0, 1, 0),       # зелений
            (0, 0, 1),       # синій
            (1, 1, 0),       # жовтий
            (1, 0, 1),       # фіолетовий
            (0, 1, 1),       # бірюзовий
            (0.8, 0.4, 0),   # коричневий
            (0.5, 0, 0.5),   # темно-фіолетовий
            (0.3, 0.7, 0.3), # світло-зелений
            (0.9, 0.5, 0.2)  # помаранчевий
        ]

    # ------------------------------------------------------
    #                 LOAD TEXTURE
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
    #                 LOAD GEOJSON DISTRICTS
    # ------------------------------------------------------

    def _load_geojson(self):
        try:
            with open(self.geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for feature in data["features"]:
                name = feature["properties"].get("name", "unknown")
                min_alt = feature["properties"].get("min_altitude", 50)
                geom = feature["geometry"]
                poly_list = []

                if geom["type"] == "Polygon":
                    # беремо лише зовнішню лінію
                    for ring in geom["coordinates"]:
                        poly_list.append(self._convert_polygon(ring))

                elif geom["type"] == "MultiPolygon":
                    for mp in geom["coordinates"]:
                        for ring in mp:  # кожен полілінг в мультиполігоні
                            poly_list.append(self._convert_polygon(ring))

                self.districts.append({
                    "name": name,
                    "min_altitude": min_alt,
                    "polygons": poly_list
                })

            print("[KyivMap] ✔ GeoJSON loaded:", len(self.districts), "districts")
        except Exception as e:
            print("[KyivMap] ❌ Failed to load GeoJSON:", e)


    # ------------------------------------------------------
    #           CONVERT LAT/LON → LOCAL SCENE X/Z
    # ------------------------------------------------------
    def _convert_polygon(self, poly):
        out = []
        for lon, lat in poly:
            # нормалізуємо координати у [0..1] від west→east, south→north
            nx = (lon - self.west) / (self.east - self.west)
            nz = (lat - self.south) / (self.north - self.south)

            # scale: від -scale → +scale
            x = (nx - 0.5) * self.scale * 2
            z = (nz - 0.5) * self.scale * 2
            out.append((x, z))
        return out

    # ------------------------------------------------------
    #                   DRAW MAP
    # ------------------------------------------------------
    def draw(self):
        if not hasattr(self, "texture"):
            return

        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        self.texture.bind()

        # Відповідність масштабу текстури і полігонів
        size_x = (self.east - self.west) / (self.east - self.west) * self.scale  # фактично self.scale
        size_z = (self.north - self.south) / (self.north - self.south) * self.scale

        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex3f(-self.scale,0,-self.scale)
        glTexCoord2f(1,0); glVertex3f(self.scale,0,-self.scale)
        glTexCoord2f(1,1); glVertex3f(self.scale,0,self.scale)
        glTexCoord2f(0,1); glVertex3f(-self.scale,0,self.scale)
        glEnd()

        self.texture.release()
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)

        # Райони
        self._draw_district_borders()

    # ------------------------------------------------------
    #                DRAW DISTRICT BORDERS
    # ------------------------------------------------------
    def _draw_district_borders(self):
        glDisable(GL_LIGHTING)

        # список кольорів для районів (можно підібрати свої)

        glLineWidth(3.0)  # товщина лінії

        for i, dist in enumerate(self.districts):
            color = self.district_colors[i % len(self.district_colors)]
            glColor3f(*color)

            for poly in dist["polygons"]:
                rotated_poly = self.rotate_polygon(poly, center=(0,0), angle_deg=0)  # наприклад 10 градусів
                mirrored_poly = self.mirror_polygon_x(rotated_poly, center_x=0)
                glBegin(GL_LINE_LOOP)
                for x, z in mirrored_poly:
                    glVertex3f(x, 0.1, z)
                glEnd()

        glLineWidth(1.0)  # повертаємо товщину до дефолтної
        glEnable(GL_LIGHTING)

    # ------------------------------------------------------
    #              FIND DISTRICT BY POINT
    # ------------------------------------------------------
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

    def get_min_altitude(self, x, z):
        d = self.find_district(x, z)
        if d:
            return d["min_altitude"]
        return 0
    
    def rotate_polygon(self, poly, center=(0,0), angle_deg=0):
        angle_rad = math.radians(angle_deg)
        cx, cz = center
        rotated = []
        for x, z in poly:
            dx, dz = x - cx, z - cz
            rx = dx * math.cos(angle_rad) - dz * math.sin(angle_rad)
            rz = dx * math.sin(angle_rad) + dz * math.cos(angle_rad)
            rotated.append((rx + cx, rz + cz))
        return rotated

    def mirror_polygon_x(self, poly, center_x=0):
        mirrored = []
        for x, z in poly:
            mx = 2*center_x - x  # дзеркало відносно center_x
            mirrored.append((mx, z))
        return mirrored
    
    def mirror_polygon_z(self, poly, center_z=0):
        mirrored = []
        for x, z in poly:
            mz = 2*center_z - z  # дзеркало відносно center_z
            mirrored.append((x, mz))
        return mirrored
    
    # отримати мін. висоту району за індексом або по позиції
    def set_min_altitude_for_district(self, district_index: int, min_alt: float):
        if 0 <= district_index < len(self.districts):
            self.districts[district_index]["min_altitude"] = float(min_alt)
            return True
        return False

    def set_min_altitude_for_district_by_name(self, name: str, min_alt: float):
        for d in self.districts:
            if d["name"] == name:
                d["min_altitude"] = float(min_alt)
                return True
        return False

    # get_min_altitude(x,z) вже викликає find_district і повертає min_altitude
    def get_min_altitude(self, x, z):
        d = self.find_district(x, z)
        if d:
            return float(d.get("min_altitude", 0))
        return 0.0

    # експортуємо тільки мапу мін. висот у JSON, щоб зберегти налаштування
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
            return True
        except Exception as e:
            print("[KyivMap] ❌ import_min_altitudes failed:", e)
            return False
        
    def draw_min_altitude_boxes(self):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for i, dist in enumerate(self.districts):
            min_alt = dist.get("min_altitude", 0)
            if min_alt <= 0:
                continue

            # 🔥 Колір району
            r, g, b = self.district_colors[i % len(self.district_colors)]
            glColor4f(r, g, b, 0.25)  # прозорий

            for poly in dist["polygons"]:
                mirrored_poly = self.mirror_polygon_x(poly)
                self._draw_extruded_polygon(mirrored_poly, min_alt)

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)


    def _draw_extruded_polygon(self, poly, height):
        """Малює екструдований полігон (нижня та верхня кришки + бокові стінки)."""
        # Верхня кришка
        glBegin(GL_POLYGON)
        for x, z in poly:
            glVertex3f(x, height, z)
        glEnd()

        # Нижня кришка
        glBegin(GL_POLYGON)
        for x, z in poly:
            glVertex3f(x, 0, z)
        glEnd()

        # Бокові стінки
        glBegin(GL_QUADS)
        for i in range(len(poly)):
            x1, z1 = poly[i]
            x2, z2 = poly[(i + 1) % len(poly)]

            glVertex3f(x1, 0, z1)
            glVertex3f(x2, 0, z2)
            glVertex3f(x2, height, z2)
            glVertex3f(x1, height, z1)

        glEnd()
