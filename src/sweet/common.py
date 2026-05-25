from typing import TypeAlias, Sequence
from enum import Enum, auto
import pygame as pg
from PIL import Image
from dataclasses import dataclass

class FileType(Enum):
    STREAM = auto()
    BATCHLIST = auto()
    BATCH = auto()
    DYNAMIC = auto()
    BACKGROUND = auto()
    NONE = auto()

class ConvertType(Enum):
    GIF = auto()
    VIDEO = auto()
    IMAGE = auto()

class SurfaceTexture(Enum):
    PGSURF = auto()
    PILIMAGE = auto()

class PathType(Enum):
    PIECEWISE = auto()
    BEZIER = auto()

class Interpolation(Enum):
    QUAD_OUT = auto()
    QUAD_IN = auto()
    QUAD = auto()
    NONE = auto()

Drawing: TypeAlias = pg.Surface | Image.Image | int
TextureData: TypeAlias = dict[Drawing, int, int]
AtlasTexture: TypeAlias = dict[int, int, int]
Vector: TypeAlias = list[int, int]
Controls: TypeAlias = Sequence[Vector] | Sequence[list[Vector, Vector, Vector]]
Group: TypeAlias = Sequence | type | object

@dataclass
class Rec:
    x: int
    y: int
    w: int
    h: int

@dataclass
class UVLocation:
    tex_id: int = ""
    uv: Rec = None

@dataclass
class CollisionData:
    mtv: int
    normal: Vector
    is_b: bool
    contact_point: Vector
    entity: object

@dataclass
class Sprite:
    texture_id: int
    uv: tuple
    pos: tuple
    scale: tuple
    rotation: tuple
    color: tuple
    perspective: bool
    static: bool
    shader: bool
    attrs: dict
    unit: int
