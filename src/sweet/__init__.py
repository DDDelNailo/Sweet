from sweet.graphics.__texture import Imaging

from . import (
    __camera,
    __common,
    __entity,
    __inputting,
    __looping,
    __testing,
    graphics,
    linalg,
    network,
)

def init():
    __looping.GameLoop.init()

def run():
    __looping.GameLoop.start()

class Entity(__entity.Entity):
    def __init__(
                self,
                pos: tuple,
                image: Imaging = None,
                scale: tuple = (0, 0),
                angle: int = 0,
                layer: int = 0,
                order: int = -1,
                pre_tick: bool = False,
                tick: bool = False,
                pos_tick: bool = False
            ):
        super().__init__(
                pos,
                image,
                scale,
                angle,
                layer,
                order,
                pre_tick,
                tick,
                pos_tick
        )
    
class Display:
    screen_size = (__looping.GameLoop.view_width, __looping.GameLoop.view_height)

    @staticmethod
    def set_size(size):
        __looping.GameLoop.set_screen_size(size)
        
    @staticmethod
    def set_resizable(value):
        __looping.GameLoop.set_resizable(value)

class Textures:
    @staticmethod
    def load_json_resource(path):
        graphics.__texture.Texture.load_json_textures(path)
    

__all__ = ["Textures", "Display"]