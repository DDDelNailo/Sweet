import numpy as np
from ..common import Geometry
import trimesh
from pathlib import Path
from .shaders import ShaderModels
from ..path_solver import solve_path
import json

class Model:
    _models: dict[str, "ModelInstance"] = {}

    @classmethod
    def get_model(cls, name: str):
        if cls._models.get(name) is None:
            model = ShaderModels.default_model(name)
            return ModelInstance(name, model)
        return cls._models[name]
    
    @classmethod
    def load_json_models(cls, path: str | Path):
        with open(path, "r") as file:
            assets = json.load(file)
            
        for asset_type in assets.keys():
            if asset_type == "models":
                models = assets[asset_type]
                for key in models.keys():
                    path = models[key]
                    absolute_path = solve_path(path)

                    cls.load_model(key, absolute_path)

    @classmethod
    def load_model(cls, name: str, path: Path) -> "ModelInstance":
        if not cls._models.get(name) == None:
            raise KeyError

        normal_path = solve_path(path)
        mesh = trimesh.load(normal_path) # type: ignore
        
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        vertices = mesh.vertices.astype(np.float32) # type: ignore
        normals = mesh.vertex_normals.astype(np.float32) # type: ignore
        faces = mesh.faces.astype(np.uint32) # type: ignore

        if hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None: # type: ignore
            uvs = mesh.visual.uv.astype(np.float32) # type: ignore
        else:
            uvs = np.zeros((len(vertices), 2), dtype=np.float32)

        interleaved_data = np.hstack((vertices, uvs, normals)).astype(np.float32)

        vbo_data = interleaved_data.flatten()
        ebo_data = faces.flatten() # type: ignore
        index_count = len(ebo_data)
        geometry = Geometry(vbo_data=vbo_data, ebo_data=ebo_data, index_count=index_count) # type: ignore
        model = ModelInstance(name, geometry)
        model.upload()
        cls._models[name] = model
        return model

class ModelInstance:
    def __init__(self, name: str, geometry: Geometry):
        self.name = name
        self.geometry = geometry

    def upload(self):
        ShaderModels.add_model(self.name, self.geometry)