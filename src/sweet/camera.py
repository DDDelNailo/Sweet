from .vector import Vec3
from dataclasses import dataclass

@dataclass
class Camera:
    name: str
    pos: Vec3
    angles: Vec3
    fov: float

class CameraManager:
    _cams: dict["str", Camera] = {"main": Camera("main", Vec3(0, 0, -1), Vec3(0, 0, 0), 70.0)}
    _main: str = "main"

    @classmethod
    def create_cam(cls, name: str) -> Camera:
        if cls._cams.get(name):
            raise KeyError
        
        cam = Camera(name, Vec3(0, 0, -1), Vec3(0, 0, 0), 70.0)
        cls._cams[name] = cam
        return cam
    
    @classmethod
    def destroy_cam(cls, name: str) -> None:
        cls._cams.pop(name)

    @classmethod
    def set_main_camera(cls, name: str) -> None:
        cls._main = name
    
    @classmethod
    def get_main_camera(cls) -> Camera:
        return cls._cams[cls._main]

    @classmethod
    def get_camera(cls, name: str) -> Camera:
        return cls._cams[name]