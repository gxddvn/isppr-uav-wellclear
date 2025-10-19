import trimesh
import os

def load_gltf_model(path: str, scale_target=50.0):
    """
    Завантажує модель .gltf або .glb, центрує її в (0,0,0) і масштабує.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Модель не знайдено: {path}")

    mesh = trimesh.load(path)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(mesh.dump())
    mesh.apply_translation(-mesh.centroid)

    scale = scale_target / max(mesh.extents) if max(mesh.extents) > 0 else 1.0
    mesh.apply_scale(scale)
    return mesh
