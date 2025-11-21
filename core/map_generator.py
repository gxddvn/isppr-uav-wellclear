import osmnx as ox
import matplotlib.pyplot as plt
from PIL import Image

def generate_kyiv_map_png(output_path="kyiv_map.png"):
    """
    Завантажує граф доріг Києва, малює його в PNG і конвертує в RGB для OpenGL.
    Повертає bounding box (west, south, east, north).
    """

    G = ox.graph_from_place("Kyiv, Ukraine", network_type="drive")

    fig, ax = ox.plot_graph(
        G,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5,
        dpi=800,
        show=False,
        close=False
    )
    temp_path = "temp_kyiv_map.png"
    fig.savefig(temp_path, dpi=800, bbox_inches="tight", pad_inches=0)
    plt.close(fig)

    im = Image.open(temp_path).convert("RGB")
    im.save(output_path)

    nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
    west, south, east, north = nodes_gdf.total_bounds

    return (west, south, east, north)

def load_kyiv_districts():
    """
    Завантажує 10 адміністративних районів Києва з OSM,
    залишає тільки name (українською, якщо доступне), admin_level і geometry.
    """
    city_gdf = ox.geocode_to_gdf("Kyiv, Ukraine")
    kyiv_polygon = city_gdf.geometry.iloc[0]

    tags = {"boundary": "administrative", "admin_level": "6"}
    gdf = ox.features_from_polygon(kyiv_polygon, tags=tags)

    gdf = gdf[gdf.geometry.within(kyiv_polygon)]

    gdf["name"] = gdf.get("name:uk", gdf.get("name"))

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

    gdf = gdf[["name", "admin_level", "geometry"]].drop_duplicates(subset="name").reset_index(drop=True)

    if len(gdf) != 10:
        print(f"Warning: знайдено {len(gdf)} елементів, очікувано 10 районів")

    gdf.to_file("app/assets/maps/kyiv_districts_clean.geojson", driver="GeoJSON")

    return gdf

