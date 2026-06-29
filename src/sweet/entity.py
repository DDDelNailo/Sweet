from .graphics.texture import Imaging
from .graphics.shaders import ShaderRender
from .graphics.model import ModelInstance, Model
import OpenGL.GL as gl
import pygame as pg
from .common import Sprite, FileType
from typing import Sequence
from .vector import Vec2, Vec3
from PIL import Image
from math import pi

class Entity:
    def __init__(self,
                 image: Imaging | None=None,
                 pos: tuple[int, int] | tuple[int, int, int]=(0, 0),
                 scale: tuple[int, int] | tuple[int, int, int]=(1, 1),
                 angle: float | tuple[float, float, float]=0,
                 layer: int=0,
                 order: int=-1,
                 pre_tick: bool=False,
                 tick: bool=False,
                 pos_tick: bool=False) -> None:
        
        self.__flat = False
        if len(pos) == 0:
            self.__flat = True
            
        if self.__flat:
            self.pos = Vec2(*pos)
            self.scale = Vec2(*scale)
            self.angle = angle
        else:
            self.pos = Vec3(*pos)

            if len(scale) == 2:
                self.scale = Vec3(scale[0], scale[1], 1)
            else:
                self.scale = Vec3(*scale)

            if isinstance(angle, float) or isinstance(angle, int):
                self.angle = Vec3(angle, 0, 0)
            else:
                self.angle = Vec3(*angle)

        if image == None:
            self.image = Imaging("image", Image.new("RGBA", (1, 1), (0, 0, 0, 0)), FileType.BATCH, gl.GL_RGBA) # type: ignore
        else:
            self.image: Imaging = image
        self.layer = int(layer)
        self.order = order
        self.mask = Mask()
        EntityManager.agend_entity(self, order, pre_tick, tick, pos_tick)
            
    def set_layer(self, layer: int, order: int | None = None) -> None:
        if order == None:
            order = self.order
        layer = int(layer)
        if not self.layer == layer:
            EntityManager.agend_layer_change(self, layer, order)

    def pos_tick(self) -> None:
        pass

    def pre_tick(self) -> None:
        pass

    def tick(self) -> None:
        pass

    def draw(self) -> None:
        pass
    
    def draw_gui(self) -> None:
        pass

    def get_mvp(self) -> None:
        pass
    
    def set_id(self, id: int) -> None:
        self._id = id

    def get_id(self) -> int:
        return self._id
    
    def __str__(self) -> str:
        return f"{type(self).__name__} - {self._id}"
    
    def destroy_self(self):
        EntityManager.agend_destroy(self)

class EntityManager:
    _entities: dict[int, dict[int, list[Entity]]] = {}
    _content_orders: list[int] = []
    _content_layers: dict[int, list[int]] = {}
    _instance_groups: dict[type[object], dict[int, Entity]] = {}

    _pre_tick: dict[int, Entity] = {}
    _tick: dict[int, Entity] = {}
    _pos_tick: dict[int, Entity] = {}

    _layer_changes: dict[int, tuple[Entity, int, int]] = {}
    _entity_changes: dict[Entity, tuple[Entity, int, bool, bool, bool]] = {}
    _destroy_changes: dict[Entity, Entity] = {}
    _id: int = 0

    @classmethod
    def add_instance(cls, instance: Entity) -> None:
        name = instance.__class__

        if cls._instance_groups.get(name) == None:
            cls._instance_groups[name] = {}

        cls._instance_groups[name][instance.get_id()] = instance

    @classmethod
    def remove_instance(cls, instance: Entity) -> None:
        name = instance.__class__
        if not cls._instance_groups.get(name) == None:
            if not cls._instance_groups[name].get(instance.get_id()) == None:
                del cls._instance_groups[name][instance.get_id()]
                if len(cls._instance_groups[name]) == 0:
                    del cls._instance_groups[name]

    @classmethod
    def get_entity_group(cls, group: type[object]) -> list[Entity]:
        return list(map(lambda x: x[1], cls._instance_groups[group].items()))

    @staticmethod
    def find_insert_index(arr: list[int], target: int) -> int:
        left, right = 0, len(arr) - 1

        while left <= right:
            mid = (left + right) // 2

            if arr[mid] == target:
                return -1
            elif arr[mid] < target:
                left = mid + 1
            else:
                right = mid - 1

        return left

    @classmethod
    def get_layer_changes(cls):
        return cls._layer_changes

    @classmethod
    def get_entity_changes(cls):
        return cls._entity_changes

    @classmethod
    def get_destroy_changes(cls):
        return cls._destroy_changes

    @classmethod
    def set_layer_change(cls, entity: Entity, layer: int, order: int) -> None:
        if hasattr(entity, "_id"):
            cls.remove_entity_layer(entity)
        entity.layer = layer
        entity.order = order
        cls.add_entity_layer(entity)

    @classmethod
    def agend_layer_change(cls, entity: Entity, layer: int, order: int) -> None:
        cls._layer_changes[entity.get_id()] = (entity, layer, order)

    @classmethod
    def agend_entity(cls, entity: Entity, order: int, pre_tick: bool, tick: bool, pos_tick: bool):
        cls._entity_changes[entity] = (entity, order, pre_tick, tick, pos_tick)

    @classmethod
    def agend_destroy(cls, entity: Entity):
        cls._destroy_changes[entity] = entity

    @classmethod
    def clear_agend(cls):
        cls._entity_changes = {}
        cls._layer_changes = {}
        cls._destroy_changes = {}

    @classmethod
    def create_entity(cls, entity: Entity, order: int, pre_tick: bool, tick: bool, pos_tick: bool) -> None:
        entity.set_id(cls._id)
        cls._id += 1
        EntityManager.add_instance(entity)

        if not order == -1:
            cls.add_entity_layer(entity)
        
        if pre_tick:
            cls.add_entity_tick(entity, 0)
        if tick:
            cls.add_entity_tick(entity, 1)
        if pos_tick:
            cls.add_entity_tick(entity, 2)

    @classmethod
    def destroy_entity(cls, entity: Entity) -> None:
        cls.remove_entity_tick(entity, 0)
        cls.remove_entity_tick(entity, 2)
        cls.remove_entity_tick(entity, 3)
        cls.remove_entity_layer(entity)
        cls.remove_instance(entity)

    @classmethod
    def add_entity_tick(cls, entity: Entity, tick_type: int) -> None:
        if tick_type == 0:
            cls._pre_tick[entity.get_id()] = entity
        elif tick_type == 1:
            cls._tick[entity.get_id()] = entity
        elif tick_type == 2:
            cls._pos_tick[entity.get_id()] = entity

    @classmethod
    def remove_entity_tick(cls, entity: Entity, tick_type: int) -> None:
        if tick_type == 0 and not cls._pre_tick.get(entity.get_id()) is None:
            cls._pre_tick.pop(entity.get_id())
        elif tick_type == 1 and not cls._tick.get(entity.get_id()) is None:
            cls._tick.pop(entity.get_id())
        elif tick_type == 2 and not cls._pos_tick.get(entity.get_id()) is None:
            cls._pos_tick.pop(entity.get_id())

    @classmethod
    def add_entity_layer(cls, entity: Entity) -> None:
        layer: int = entity.layer
        order: int = entity.order

        if cls._entities.get(order) == None:
            cls._entities[order] = {layer: [entity]}
        else:
            if cls._entities[order].get(layer) == None:
                cls._entities[order][layer] = []
            cls._entities[order][layer].append(entity)
        
        index = cls.find_insert_index(cls._content_orders, order)
        if not index == -1:
            cls._content_orders.insert(index, order)

        if cls._content_layers.get(order) == None:
            cls._content_layers[order] = [layer]
        else:
            index = cls.find_insert_index(cls._content_layers[order], layer)
            if not index == -1:
                cls._content_layers[order].insert(index, layer)

    @classmethod
    def remove_entity_layer(cls, entity: Entity) -> None:
        layer: int = entity.layer
        order: int = entity.order

        if order not in cls._entities:
            return
        if layer not in cls._entities[order]:
            return

        layer_list: list[Entity] = cls._entities[order][layer]
        layer_list.remove(entity)

        if not layer_list:
            cls._content_layers[order].remove(layer)
            del cls._entities[order][layer]

            if not cls._content_layers[order]:
                cls._content_layers.pop(order)
                cls._content_orders.remove(order)

                del cls._entities[order]

    @classmethod
    def get_all_entities(cls):
        return cls._entities

    @classmethod
    def get_tick_entities(cls, tick_type: int) -> dict[int, Entity]:
        if tick_type == 0:
            return cls._pre_tick
        elif tick_type == 1:
            return cls._tick
        elif tick_type == 2:
            return cls._pos_tick
        raise ValueError("Insira um tipo válido.")

    @classmethod
    def get_content_orders(cls) -> list[int]:
        return cls._content_orders

    @classmethod
    def get_content_layers(cls, order: int) -> list[int]:
        return cls._content_layers[order]

class Draw:
    _state_attr: dict[str, tuple[int | float, ...]] = {}
    _state_shader: str = "__def__"

    @classmethod
    def set_state_shader(cls, name: str) -> None:
        cls._state_shader = name
        cls.clear_state_shader()

    @classmethod
    def clear_state_shader(cls):
        cls._state_attr = {}

    @classmethod
    def set_shader_attr(cls, name: str, *values: int | float) -> None:
        cls._state_attr[name] = values

    @classmethod
    def draw_image(cls,
                   model: ModelInstance,
                   image: Imaging | None,
                   pos: Vec3,
                   scale: Vec3,
                   angle: Vec3,
                   color: tuple[int | float, int | float, int | float, int | float]=(255, 255, 255, 255),
                   perspective: bool=True,
                   static: bool=False) -> None:

        color = (color[0] / 255, color[1] / 255, color[2] / 255, color[3] / 255)
        angle = Vec3(angle.x * pi / 180, angle.y * pi / 180, angle.z * pi / 180)

        sprite = Sprite(
                        model.name,
                        image if image is None else image.uv,
                        pos.unp(),
                        scale.unp(),
                        angle.unp(),
                        color,
                        perspective,
                        static,
                        cls._state_shader,
                        cls._state_attr)
        
        ShaderRender.add_draw_call(sprite)

    @classmethod
    def set_font(cls, font: pg.font.Font) -> None:
        cls._font = font

    @classmethod
    def get_font(cls) -> pg.font.Font:
        return cls._font

    @classmethod
    def draw_text(cls,
                image: Imaging,
                text: str,
                pos: Vec3,
                scale: Vec3,
                angle: Vec3 = Vec3(0, 0, 0),
                color: tuple[int, int, int] = (255, 255, 255),
                alpha: float = 1,
                static: bool = True,
                align: tuple[int, int]=(0, 0),) -> None: # type: ignore
        font_surf: pg.Surface = cls.get_font().render(text, True, (255, 255, 255)) # type: ignore
        width: int
        height: int

        data = pg.image.tostring(font_surf, "RGBA", True)
        size = font_surf.get_size() # type: ignore
        new_image = Image.frombytes("RGBA", size, data)
        image.set_image(new_image)
        image.upload()

        width, height = (image.get_width(), image.get_height())
        cls.draw_image(
                       Model.get_model("__flat__"),
                       image,
                       Vec3(pos[0] + width * scale[0] * align[0] / 2, pos[1] + height * scale[1] * align[1] / 2, pos[2]),
                       Vec3(width * scale[0], height * scale[1], 1),
                       angle=angle,
                       color=(*color, alpha),
                       static=static)

class Polygon:
    def __init__(self, vertices: Sequence[Vec2]) -> None:
        self.vertices = vertices

    def rotate(self, angle: float) -> "Polygon":
        vertices = [vertex.rotate(angle) for vertex in self.vertices]
        return Polygon(vertices)

    def translate(self, pos: Vec2) -> "Polygon":
        vertices = [vertex + pos for vertex in self.vertices]
        return Polygon(vertices)

    def scale(self, multiplier: Vec2) -> "Polygon":
        vertices = [Vec2(vertex.x * multiplier.x, vertex.y * multiplier.y) for vertex in self.vertices]
        return Polygon(vertices)

class Mask:
    def __init__(self):
        self.polygons: dict[str, Polygon] = {}

    def add_polygon(self, name: str, polygon: Polygon) -> None:
        self.polygons[name] = polygon

    def get_polygon(self, name: str) -> Polygon:
        return self.polygons[name]
    
    def def_polygon(self) -> Polygon:
        first = list(self.polygons.keys())[0]
        return self.polygons[first]
