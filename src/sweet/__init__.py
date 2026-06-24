from sweet.graphics.texture import Imaging # type: ignore
from sweet.vector import Vec2, Vec3 # type: ignore
from pathlib import Path

from . import (
    camera, # type: ignore
    common, # type: ignore
    entity, # type: ignore
    graphics, # type: ignore
    inputting, # type: ignore
    linalg, # type: ignore
    looping, # type: ignore
    network, # type: ignore
    path_solver, # type: ignore
)

def init():
    looping.GameLoop.init()

def run():
    looping.GameLoop.start()

# class Scene:
#     @staticmethod
#     def add_entity(obj: type[object], *context: Any):
#         entity.EntityManager.agend_entity()

class Entity(entity.Entity):
    def __init__(
                self,
                image: Imaging | None = None,
                pos: tuple[int, int] | tuple[int, int, int] = (0, 0),
                scale: tuple[int, int] | tuple[int, int, int] = (1, 1),
                angle: float | tuple[float, float, float] = 0,
                layer: int = 0,
                order: int = -1,
                pre_tick: bool = False,
                tick: bool = False,
                pos_tick: bool = False
            ):
        super().__init__(
                image,
                pos,
                scale,
                angle,
                layer,
                order,
                pre_tick,
                tick,
                pos_tick
        )
    
class Display:
    screen_size = (looping.GameLoop.view_width, looping.GameLoop.view_height)

    @staticmethod
    def set_shader(name: str):
        entity.Draw.set_state_shader(name)

    @staticmethod
    def add_shader(path_vertex: str, path_fragment: str, name: str | None=None):
        if name is None:
            # Extracts the file name of the vertex shaders without the extension
            name = path_vertex.split("/")[-1].split(".")[0]
            
        graphics.shaders.ShaderManager.add_shader(name, path_vertex, path_fragment)

    @staticmethod
    def size(size: tuple[int, int]) -> None:
        looping.GameLoop.set_screen_size(size)
        
    @staticmethod
    def resizable(value: bool) -> None:
        looping.GameLoop.set_resizable(value)
        
    @staticmethod
    def background(color: tuple[int, int, int, int]) -> None:
        looping.GameLoop.set_background_color(color)
        
    @staticmethod
    def maximizable(value: bool) -> None:
        looping.GameLoop.set_can_fullscreen(value)
    
    @staticmethod
    def is_maximized() -> bool:
        return looping.GameLoop.get_fullscreen()
    
    @staticmethod
    def title(text: str) -> None:
        looping.GameLoop.set_title(text)
    
    @staticmethod
    def icon(image: Imaging) -> None:
        looping.GameLoop.set_icon(image.get_image())

class Textures:
    @staticmethod
    def load_json_resource(path: str | Path) -> None:
        graphics.texture.Texture.load_json_textures(path)
    
    @staticmethod
    def get(name: str):
        return graphics.texture.Texture.get_texture(name)

class Animations:
    @staticmethod
    def load_json_resource(path: str | Path) -> None:
        graphics.texture.Animation.load_json_textures(path)
    
    @staticmethod
    def get(name: str):
        return graphics.texture.Animation.get_video(name)

__all__ = ["Textures", "Display"]