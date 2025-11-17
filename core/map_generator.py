import osmnx as ox
import matplotlib.pyplot as plt
from PIL import Image

def generate_kyiv_map_png(output_path="kyiv_map.png"):
    """
    Завантажує граф доріг Києва, малює його в PNG і конвертує в RGB для OpenGL.
    Повертає bounding box (west, south, east, north).
    """

    # 1. Завантажуємо граф доріг Києва
    G = ox.graph_from_place("Kyiv, Ukraine", network_type="drive")

    # 2. Малюємо граф у PNG
    fig, ax = ox.plot_graph(
        G,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5,
        dpi=800,         # можна змінити dpi при потребі
        show=False,
        close=False
    )
    temp_path = "temp_kyiv_map.png"
    fig.savefig(temp_path, dpi=800, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    # 3. Конвертуємо у RGB для OpenGL
    im = Image.open(temp_path).convert("RGB")
    im.save(output_path)

    # 4. Отримуємо bounding box з координат вузлів графа
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
    west, south, east, north = nodes_gdf.total_bounds

    return (west, south, east, north)

def load_kyiv_districts():
    """
    Завантажує 10 адміністративних районів Києва з OSM,
    залишає тільки name (українською, якщо доступне), admin_level і geometry.
    """
    # 1. Отримуємо полігон Києва
    city_gdf = ox.geocode_to_gdf("Kyiv, Ukraine")
    kyiv_polygon = city_gdf.geometry.iloc[0]

    # 2. Завантажуємо admin_level=6 всередині полігону Києва
    tags = {"boundary": "administrative", "admin_level": "6"}
    gdf = ox.features_from_polygon(kyiv_polygon, tags=tags)

    # 3. Фільтруємо лише ті, що дійсно всередині Києва
    gdf = gdf[gdf.geometry.within(kyiv_polygon)]

    # 4. Формуємо назву: name:uk або fallback на name
    gdf["name"] = gdf.get("name:uk", gdf.get("name"))

    # 5. Залишаємо лише 10 основних районів
    district_names = [
        "Голосіївський район",
        "Солом’янський район",
        "Святошинський район",
        "Дарницький район",
        "Дніпровський район",
        "Деснянський район",
        "Оболонський район",
        "Подільський район",
        "Печерський район",
        "Шевченківський район"
    ]
    gdf = gdf[gdf["name"].isin(district_names)]

    # 6. Залишаємо потрібні колонки і прибираємо дублікати
    gdf = gdf[["name", "admin_level", "geometry"]].drop_duplicates(subset="name").reset_index(drop=True)

    # 7. Перевірка: маємо саме 10 районів
    if len(gdf) != 10:
        print(f"Warning: знайдено {len(gdf)} елементів, очікувано 10 районів")

    # 8. Зберігаємо GeoJSON
    gdf.to_file("app/assets/maps/kyiv_districts_clean.geojson", driver="GeoJSON")

    return gdf

