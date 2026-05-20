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

def start():
    looping.GameLoop.start()