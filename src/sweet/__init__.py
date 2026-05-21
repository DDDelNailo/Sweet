from sweet.graphics.texture import Imaging

from . import (
    graphics,
    linalg,
    camera,
    network,
    inputting,
    looping,
    testing,
    entity,
    common,
)

def init():
    looping.GameLoop.init()

def run():
    looping.GameLoop.start()

class Entity(entity.Entity):
    def __init__(
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