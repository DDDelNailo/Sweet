from sweet.graphics.texture import Imaging
from sweet.vector import Vec2, Vec3

from . import (
    camera,
    common,
    entity,
    graphics,
    inputting,
    linalg,
    looping,
    network,
    testing,
    path_solver,
)

def init():
    looping.GameLoop.init()

def run():
    looping.GameLoop.start()

class Entity(entity.Entity):
    def __init__(
                self,
                image: Imaging = None,
                pos: tuple = (0, 0),
                scale: tuple = (1, 1),
                angle: float | tuple = 0,
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

    def set_shader(name):
        entity.Draw._state_shader = name

    def add_shader(path_vertex, path_fragment, name=None):
        if name is None:
            # Extracts the file name of the vertex shaders without the extension
            name = path_vertex.split("/")[-1].split(".")[0]
            
        graphics.shaders.ShaderManager.add_shader(name, path_vertex, path_fragment)

    @staticmethod
    def size(size):
        looping.GameLoop.set_screen_size(size)
        
    @staticmethod
    def resizable(value):
        looping.GameLoop.set_resizable(value)
        
    @staticmethod
    def background(color):
        looping.GameLoop.set_background_color(color)
        
    @staticmethod
    def maximizable(value):
        looping.GameLoop.set_can_fullscreen(value)
    
    @staticmethod
    def is_maximized():
        return looping.GameLoop.get_fullscreen()
    
    @staticmethod
    def title(text: str) -> None:
        looping.GameLoop.set_caption(text)
    
    @staticmethod
    def icon(image: Imaging) -> None:
        looping.GameLoop.set_icon(image)

class Textures:
    @staticmethod
    def load_json_resource(path):
        graphics.texture.Texture.load_json_textures(path)
    
    @staticmethod
    def get(name):
        return graphics.texture.Texture.get_texture(name)

__all__ = ["Textures", "Display"]