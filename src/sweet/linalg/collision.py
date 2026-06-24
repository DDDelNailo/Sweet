from pygame.locals import * # type: ignore
from ..vector import Vec2
from typing import Sequence, Any
from collections.abc import Callable
from ..common import CollisionData
from ..entity import EntityManager, Polygon, Entity

class Collision:
    @classmethod
    def collision_list(cls, element: Entity, group: type | Sequence[Entity], polygon_a: Polygon | None = None, polygon_b: Polygon | None = None, order: bool=True, apply_func: Callable[[Entity, Entity, CollisionData], Any] | None = None) -> list[CollisionData]:
        if polygon_a == None: polygon_a = element.mask.def_polygon()

        if isinstance(group, type):
            group = EntityManager.get_entity_group(group)

        result: list[CollisionData] = []

        for other in group:
            if not polygon_b == None:
                use_polygon_b = polygon_b
            else:
                use_polygon_b = other.mask.def_polygon()

            collision = cls.colliding(element, other, polygon_a, use_polygon_b)
            if isinstance(collision, CollisionData):
                if apply_func:
                    apply_func(element, other, collision)

                result.append(collision)

        if order:
            result.sort(key=lambda x: x.mtv.magnitude())
            
        return result

    @staticmethod
    def colliding(a: Entity, b: Entity, polygon_a: Polygon, polygon_b: Polygon) -> CollisionData | bool:
        lowest_overlap: float = float("inf")
        overlap_axis: Vec2 = Vec2(0, 0)
        is_b: bool = False
        if isinstance(a.pos, Vec2) and isinstance(b.pos, Vec2):
            x1, x2 = polygon_a.translate(a.pos), polygon_b.translate(b.pos)
        else:
            return False # Implement 3D
        
        contact_point = Vec2(0, 0)

        for shape in (x1, x2):
            verts = shape.vertices
            for i in range(len(verts)):
                v1: Vec2 = verts[i]
                v2: Vec2 = verts[(i + 1) % len(verts)]

                axis: Vec2 = (v2 - v1).rotate90().normalize()

                min_a: float = float("inf")
                max_a: float = float("-inf")
                for v in x1.vertices:
                    p: float = axis.dot(v)
                    min_a: float = min(min_a, p)
                    max_a: float = max(max_a, p)

                min_b: float = float("inf")
                max_b: float = float("-inf")
                for v in x2.vertices:
                    p: float = axis.dot(v)
                    min_b: float = min(min_b, p)
                    max_b: float = max(max_b, p)

                if max_a <= min_b or max_b <= min_a:
                    return False

                overlap: float = min(max_a, max_b) - max(min_a, min_b)
        
                if overlap < lowest_overlap:
                    lowest_overlap: float = overlap
                    
                    direction: Vec2 = (b.pos - a.pos)
                    if axis.dot(direction) < 0:
                        axis: Vec2 = -axis

                    overlap_axis: Vec2 = axis

        mtv = (overlap_axis * lowest_overlap)
        if isinstance(mtv, Vec2):
            return CollisionData(mtv=mtv, normal=overlap_axis, is_b=is_b, contact_point=contact_point, entity=b)
        return CollisionData(mtv=Vec2(0, 0), normal=overlap_axis, is_b=is_b, contact_point=contact_point, entity=b)