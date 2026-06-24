from ..common import ConvertType, Rec, UVLocation, Sprite
import pygame as pg
import OpenGL.GL as gl
from OpenGL.GL.shaders import compileProgram, compileShader # type: ignore
import ctypes
import glm
import numpy as np
from collections.abc import Callable
from typing import Any
import uuid
from PIL import Image
from dataclasses import dataclass, field
from ..camera import CameraManager
from ..path_solver import solve_path
from pathlib import Path
from numpy.typing import NDArray
import numpy as np

@dataclass
class Attribute:
    name: str
    location: int
    size: int
    gl_type: int
    offset: int

@dataclass
class BufferLayout:
    stride: int
    attributes: list[Attribute]

@dataclass
class VertexArrayState:
    vao: int
    quad_vbo: int
    instance_vbo: int | None
    ebo: int | None

    quad_layout: BufferLayout
    instance_layout: BufferLayout | None

@dataclass
class UniformMember:
    name: str
    gl_type: int
    size: int
    offset: int
    array_stride: int
    matrix_stride: int

@dataclass
class UniformBlock:
    name: str
    index: int
    binding: int
    data_size: int
    members: list[UniformMember] = field(default_factory=lambda: list[UniformMember]())

    buffer_id: int | None = None

@dataclass
class StorageBlock:
    name: str
    binding: int
    size: int

    buffer_id: int

@dataclass
class ShaderResources:
    ubos: dict[str, UniformBlock]
    ssbos: dict[str, StorageBlock]

class Atlas:
    def __init__(self, width: int, height: int, occupation: str, padding: int=0) -> None:
        self.occupation = occupation
        self.width = width
        self.height = height
        self.padding = padding
        self.tex_id = -1

        self.image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        initial = Rec(0, 0, width, height)
        self.free_rects: dict[tuple[int, int, int, int], Rec] = {(initial.x, initial.y, initial.w, initial.h): initial}
        self.used_rects: dict[tuple[int, int, int, int], Rec] = {}

    def insert(self, w: int, h: int) -> Rec | None:
        w += self.padding
        h += self.padding

        best = None
        best_score = float("inf")

        for r in self.free_rects.values():
            if w <= r.w and h <= r.h:
                leftover_h = abs(r.h - h)
                leftover_w = abs(r.w - w)
                short_side = min(leftover_h, leftover_w)

                if short_side < best_score:
                    best = Rec(r.x, r.y, w, h)
                    best_score = short_side

        if best is None:
            return None

        self._place(best)
        return Rec(best.x, best.y, w - self.padding, h - self.padding)

    def _place(self, rect: Rec):
        new_free: list[Rec] = []

        for free in self.free_rects.values():
            if not self._intersect(rect, free):
                new_free.append(free)
                continue

            if rect.x > free.x:
                new_free.append(Rec(free.x, free.y, rect.x - free.x, free.h))

            if rect.x + rect.w < free.x + free.w:
                new_free.append(Rec(
                    rect.x + rect.w,
                    free.y,
                    (free.x + free.w) - (rect.x + rect.w),
                    free.h
                ))

            if rect.y > free.y:
                new_free.append(Rec(free.x, free.y, free.w, rect.y - free.y))

            if rect.y + rect.h < free.y + free.h:
                new_free.append(Rec(
                    free.x,
                    rect.y + rect.h,
                    free.w,
                    (free.y + free.h) - (rect.y + rect.h)
                ))

        pruned = self._prune(new_free)
        self.free_rects = {
            (r.x, r.y, r.w, r.h): r for r in pruned
        }
        self.used_rects[(rect.x, rect.y, rect.w, rect.h)] = rect

    def _intersect(self, a: Rec, b: Rec):
        return not (
            a.x >= b.x + b.w or
            a.x + a.w <= b.x or
            a.y >= b.y + b.h or
            a.y + a.h <= b.y
        )

    def _contains(self, a: Rec, b: Rec):
        return (
            a.x <= b.x and
            a.y <= b.y and
            a.x + a.w >= b.x + b.w and
            a.y + a.h >= b.y + b.h
        )

    def _prune(self, rects: list[Rec]):
        pruned: list[Rec] = []
        for i, r in enumerate(rects):
            contained = False
            for j, other in enumerate(rects):
                if i != j and self._contains(other, r):
                    contained = True
                    break
            if not contained:
                pruned.append(r)
        return pruned
    
    def remove(self, rect: "Rec") -> bool:
        key = (rect.x, rect.y, rect.w, rect.h)

        if key not in self.used_rects:
            return False

        del self.used_rects[key]

        self.free_rects[key] = Rec(rect.x, rect.y, rect.w, rect.h)

        self._merge_free_rects()

        return True

    def _merge_free_rects(self) -> None:
        merged = True
        
        while merged:
            merged = False
            rects = list(self.free_rects.values())

            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    a = rects[i]
                    b = rects[j]

                    merged_rect = self._try_merge(a, b)
                    if merged_rect:
                        del self.free_rects[(a.x, a.y, a.w, a.h)]
                        del self.free_rects[(b.x, b.y, b.w, b.h)]

                        self.free_rects[
                            (merged_rect.x, merged_rect.y, merged_rect.w, merged_rect.h)
                        ] = merged_rect

                        merged = True
                        break
                if merged:
                    break

        pruned = self._prune(list(self.free_rects.values()))
        self.free_rects = {
            (r.x, r.y, r.w, r.h): r for r in pruned
        }

    def _try_merge(self, a: "Rec", b: "Rec") -> Rec | None:
        if a.y == b.y and a.h == b.h:
            if a.x + a.w == b.x:
                return Rec(a.x, a.y, a.w + b.w, a.h)
            if b.x + b.w == a.x:
                return Rec(b.x, b.y, a.w + b.w, a.h)

        if a.x == b.x and a.w == b.w:
            if a.y + a.h == b.y:
                return Rec(a.x, a.y, a.w, a.h + b.h)
            if b.y + b.h == a.y:
                return Rec(b.x, b.y, a.w, a.h + b.h)

        return None

class ShaderTexture:
    _atlas_size = 1024
    _atlas_array: list[Atlas] = []
    _atlas_loc: dict[int, Atlas] = {}
    _occupated_textures: dict[str, int] = {}

    @classmethod
    def get_atlas_size(cls):
        return cls._atlas_size

    @classmethod
    def new_atlas(cls) -> None:
        atlas = Atlas(cls._atlas_size, cls._atlas_size, uuid.uuid4().hex)
        location = cls.create_texture(atlas.image, ConvertType.IMAGE, atlas.occupation)
        atlas.tex_id = location.tex_id
        cls._atlas_array.append(atlas)
        cls._atlas_loc[location.tex_id] = atlas

    @classmethod
    def get_current_atlas(cls, width: int, height: int) -> tuple[Atlas, Rec]:
        for atlas in cls._atlas_array:
            rect = atlas.insert(width, height)
            if not rect == None:
                return atlas, rect

        cls.new_atlas()
        atlas = cls._atlas_array[-1]
        rect = atlas.insert(width, height)

        assert rect is not None, f"O novo Atlas é pequeno demais para o tamanho {width}x{height}."

        return atlas, rect

    @classmethod
    def get_atlas(cls, tex_id: int) -> Atlas:
        return cls._atlas_loc[tex_id]

    @classmethod
    def texture_to_bytes(cls, texture: Image.Image | np.ndarray, convert_type: ConvertType) -> tuple[bytes | Image.Image | NDArray[np.uint8], int, int, int]:
        if isinstance(texture, Image.Image):
            if convert_type == ConvertType.VIDEO:
                return cls._video_to_bytes(texture)
            elif convert_type == ConvertType.IMAGE:
                return cls._image_to_bytes(texture)
            raise TypeError("Tipo de conversão inválido.")
        else:
            if convert_type == ConvertType.GIF:
                return cls._gif_to_bytes(texture)
            raise TypeError("Tipo de conversão inválido.")

    @staticmethod
    def _image_to_bytes(texture: Image.Image) -> tuple[bytes, int, int, int]:
        texture = texture.convert("RGBA")
        width, height = texture.size
        bytes_texture = texture.tobytes()
        return bytes_texture, width, height, gl.GL_RGBA # type: ignore
 
    @staticmethod
    def _gif_to_bytes(texture: np.ndarray) -> tuple[NDArray[np.uint8], int, int, int]:
        height: int
        width: int
        height, width = texture.shape[:2]

        if texture.shape[2] == 3:
            image_format: int = gl.GL_RGB # type: ignore
        else:
            image_format: int = gl.GL_RGBA # type: ignore

        texture = np.ascontiguousarray(texture)

        return texture, width, height, image_format # type: ignore

    @staticmethod
    def _video_to_bytes(texture: Image.Image) -> tuple[Image.Image, int, int, int]:
        height: int
        width: int
        height, width = texture.shape[:2] # type: ignore
        array_texture = np.ascontiguousarray(texture)
        return array_texture, width, height, gl.GL_BGR # type: ignore

    @classmethod
    def create_texture_atlas_list(cls, frames: list[Image.Image], convert_type: ConvertType, location: list[UVLocation]) -> list[UVLocation]:
        uv_list: list[UVLocation] = []
        for i, frame in enumerate(frames):
            if len(location) == 0:
                loc = UVLocation()
            else:
                loc = location[i]
                
            uv = cls.create_texture_atlas(frame, convert_type, loc)
            uv_list.append(uv)

        return uv_list

    @classmethod
    def update_texture_atlas_list(cls, frames: list[Image.Image], convert_type: ConvertType, location: list[UVLocation]) -> None:
        for i, frame in enumerate(frames):
            cls.update_texture_atlas(frame, convert_type, location[i])

    @classmethod
    def delete_texture_atlas_list(cls, location: list[UVLocation]) -> None:
        for loc in location:
            cls.delete_texture_atlas(loc)

    @classmethod
    def create_texture_atlas(cls, texture: Image.Image, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)

        if not location.tex_id == -1:
            key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)
            atlas = cls.get_atlas(location.tex_id)

            if not atlas.used_rects.get(key) == None:
                if not width == location.uv.w or not height == location.uv.h:
                    raise ValueError("Tamanhos não batem")
                cls.update_texture_atlas(texture, convert_type, location)
                return location

        current_atlas, rect = cls.get_current_atlas(width, height)

        gl.glBindTexture(gl.GL_TEXTURE_2D, current_atlas.tex_id) # type: ignore
        gl.glTexSubImage2D(
            gl.GL_TEXTURE_2D, # type: ignore
            0,
            rect.x, rect.y,
            rect.w, rect.h,
            image_format,
            gl.GL_UNSIGNED_BYTE, # type: ignore
            image
        )
        return UVLocation(current_atlas.tex_id, rect)

    @classmethod
    def update_texture_atlas(cls, texture: Image.Image, convert_type: ConvertType, location: UVLocation):
        image, _, _, image_format = cls.texture_to_bytes(texture, convert_type)
        gl.glBindTexture(gl.GL_TEXTURE_2D, location.tex_id) # type: ignore
        gl.glTexSubImage2D(
            gl.GL_TEXTURE_2D, # type: ignore
            0,
            location.uv.x, location.uv.y,
            location.uv.w, location.uv.h,
            image_format,
            gl.GL_UNSIGNED_BYTE, # type: ignore
            image
        )

    @classmethod
    def delete_texture_atlas(cls, location: UVLocation) -> None:
        key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)

        atlas: Atlas = cls.get_atlas(location.tex_id)
        if not atlas.used_rects.get(key) == None:
            atlas.remove(location.uv)

            if len(atlas.used_rects) == 0 and len(cls._atlas_array) >= 2:
                cls.delete_texture(atlas.occupation)
                del cls._atlas_loc[atlas.tex_id]
                cls._atlas_array.remove(atlas)

    @classmethod
    def create_texture(cls, texture: Image.Image, convert_type: ConvertType, occupation: str | None=None) -> UVLocation:
        if occupation == None:
            occupation = uuid.uuid4().hex
            
        if not cls._occupated_textures.get(occupation) == None:
            tex_id = cls._occupated_textures[occupation]
            width, height = cls.update_texture(tex_id, texture, convert_type)

            return UVLocation(tex_id, Rec(x=0, y=0, w=width, h=height))
            
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)
        tex_id = gl.glGenTextures(1) # type: ignore

        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id) # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE) # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE) # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST) # type: ignore
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST) # type: ignore

        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, # type: ignore
            0,
            gl.GL_RGBA, # type: ignore
            width,
            height,
            0,
            image_format,
            gl.GL_UNSIGNED_BYTE, # type: ignore
            image)

        # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        # glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_LINEAR)
        # glTexEnvf(GL_TEXTURE_FILTER_CONTROL, GL_TEXTURE_LOD_BIAS, -2)
        # glGenerateMipmap(GL_TEXTURE_2D)

        cls._occupated_textures[occupation] = tex_id
        return UVLocation(tex_id, uv=Rec(x=0, y=0, w=width, h=height))
    
    @classmethod
    def update_texture(cls, tex_id: int, texture: Image.Image, convert_type: ConvertType) -> tuple[int, int]:
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id) # type: ignore
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, # type: ignore
            0,
            gl.GL_RGBA, # type: ignore
            width, height,
            0,
            image_format,
            gl.GL_UNSIGNED_BYTE, # type: ignore
            image
        )

        return width, height
    
    @classmethod
    def delete_texture(cls, occupation: str) -> None:
        gl.glDeleteTextures([cls._occupated_textures[occupation]])
        cls._occupated_textures.pop(occupation)

    @classmethod
    def get_texture_id(cls, occupation: str) -> int:
        return cls._occupated_textures[occupation]
    
class Shader:
    def __init__(self, name:str, vertex: str, fragment: str) -> None:
        self.built = False
        self.name = name
        self.vertex = vertex
        self.fragment = fragment

    def set_state(self, vertex_state: VertexArrayState, resources: ShaderResources) -> None:
        self.vertex_state = vertex_state
        self.resources = resources

    def set_program(self, program: int):
        self.program = program

class ShaderManager:
    _current_program: Shader = Shader("", "", "")
    _UNIFORM_FUNCS: dict[str, Callable[[str, Any], None]] = { # type: ignore
        "1i": gl.glUniform1i, # type: ignore
        "2i": gl.glUniform2i, # type: ignore
        "3i": gl.glUniform3i, # type: ignore
        "4i": gl.glUniform4i, # type: ignore
        "1f": gl.glUniform1f, # type: ignore
        "2f": gl.glUniform2f, # type: ignore
        "3f": gl.glUniform3f, # type: ignore
        "4f": gl.glUniform4f, # type: ignore
        "1fv": gl.glUniform1fv, # type: ignore
        "2fv": gl.glUniform2fv, # type: ignore
        "3fv": gl.glUniform3fv, # type: ignore
        "4fv": gl.glUniform4fv # type: ignore
    }

    _GL_TYPE_SIZES: dict[int, int] = {
        gl.GL_FLOAT: 1, # type: ignore
        gl.GL_FLOAT_VEC2: 2, # type: ignore
        gl.GL_FLOAT_VEC3: 3, # type: ignore
        gl.GL_FLOAT_VEC4: 4, # type: ignore

        gl.GL_INT: 1, # type: ignore
        gl.GL_INT_VEC2: 2, # type: ignore
        gl.GL_INT_VEC3: 3, # type: ignore
        gl.GL_INT_VEC4: 4, # type: ignore

        gl.GL_FLOAT_MAT4: 16, # type: ignore
    }
    _shaders: dict[str, Shader] = {}
    
    @classmethod
    def _get_uniform_function(cls, data_type: str):
        return cls._UNIFORM_FUNCS[data_type]

    @classmethod
    def set_uniform_value(cls, uniform: str, data_type: str, *value: tuple[int | float]) -> None:
        current_shader = cls.get_current_shader()
        u = gl.glGetUniformLocation(current_shader.program, uniform)
        func = cls._get_uniform_function(data_type)
        list_value = list(value)
        params = [u] + list_value
        func(*params)

    @classmethod
    def add_shader(cls, name: str, path_vertex: str | Path, path_fragment: str | Path) -> None:
        absolute_vertex = solve_path(path_vertex)
        absolute_fragment = solve_path(path_fragment)
        with open(absolute_vertex, "r") as file:
            VERTEX_SHADER = file.read()
        with open(absolute_fragment, "r") as file:
            FRAGMENT_SHADER = file.read()

        cls._shaders[name] = Shader(name=name, vertex=VERTEX_SHADER, fragment=FRAGMENT_SHADER)
        cls.build_shader(cls._shaders[name])

    @classmethod
    def build_shader(cls, shader: Shader) -> None:
        if shader.built == False:
            vertex, fragment = shader.vertex, shader.fragment
            shader.set_program(cls.compile_shader(vertex, fragment))
            cls.build_buffers(shader)

    @classmethod
    def build_all_shaders(cls) -> None:
        for shader in cls._shaders.values():
            cls.build_shader(shader)

    @classmethod
    def reflect_ubos(cls, program: int) -> dict[str, UniformBlock]:
        result: dict[str, UniformBlock] = {}

        block_count = gl.glGetProgramiv(program, gl.GL_ACTIVE_UNIFORM_BLOCKS) # type: ignore

        ubo = gl.glGenBuffers(1) # type: ignore
        gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, ubo) # type: ignore

        for block_index in range(block_count):

            length = ctypes.c_int()
            gl.glGetActiveUniformBlockiv(program, block_index, gl.GL_UNIFORM_BLOCK_NAME_LENGTH, length) # type: ignore
            name_length = length.value

            block_name = gl.glGetActiveUniformBlockName(program, block_index, name_length) # type: ignore
            block_name = bytes(block_name[1][:-1]).decode()

            size = ctypes.c_int()
            gl.glGetActiveUniformBlockiv(program, block_index, gl.GL_UNIFORM_BLOCK_DATA_SIZE, size) # type: ignore
            block_size = size.value

            bind = ctypes.c_int()
            gl.glGetActiveUniformBlockiv(program, block_index, gl.GL_UNIFORM_BLOCK_BINDING, bind) # type: ignore
            binding = bind.value

            count = ctypes.c_int()
            gl.glGetActiveUniformBlockiv(program, block_index, gl.GL_UNIFORM_BLOCK_ACTIVE_UNIFORMS, count) # type: ignore
            uniform_count = count.value

            indices = (gl.GLuint * uniform_count)()
            gl.glGetActiveUniformBlockiv(program, block_index, gl.GL_UNIFORM_BLOCK_ACTIVE_UNIFORM_INDICES, indices) # type: ignore
            uniform_indices = list(indices)

            if isinstance(uniform_indices, int):
                uniform_indices = [uniform_indices]

            block = UniformBlock(name=block_name, index=block_index, binding=binding, data_size=block_size,)

            for uniform_index in uniform_indices:
                name, size, gl_type = gl.glGetActiveUniform(program, uniform_index)
                indices = [uniform_index]
                params = (ctypes.c_int * 1)()
                gl.glGetActiveUniformsiv(program, 1, indices, gl.GL_UNIFORM_OFFSET, params) # type: ignore
                offset = params[0]

                params = (ctypes.c_int * 1)()
                gl.glGetActiveUniformsiv(program, 1, indices, gl.GL_UNIFORM_ARRAY_STRIDE, params) # type: ignore
                array_stride = params[0]

                params = (ctypes.c_int * 1)()
                gl.glGetActiveUniformsiv(program, 1, indices, gl.GL_UNIFORM_MATRIX_STRIDE, params) # type: ignore
                matrix_stride = params[0]

                member = UniformMember(
                    name=name.decode(),
                    gl_type=cls._GL_TYPE_SIZES[gl_type],
                    size=size,
                    offset=offset,
                    array_stride=array_stride,
                    matrix_stride=matrix_stride,
                )

                block.members.append(member)

            gl.glBufferData(gl.GL_UNIFORM_BUFFER, block.data_size, None, gl.GL_DYNAMIC_DRAW) # type: ignore
            gl.glBindBufferBase(gl.GL_UNIFORM_BUFFER, block.binding, ubo) # type: ignore

            block.buffer_id = ubo

            result[block.name] = block

        return result

    # @staticmethod
    # def reflect_ssbos(program: int) -> dict[str, StorageBlock]:
    #     result = {}

    #     block_count = glGetProgramiv(program, GL_SHADER_STORAGE_BLOCKS)

    #     for block_index in range(block_count):
    #         block_name = glGetActiveShaderStorageBlockName(program, block_index)
    #         block_size = glGetActiveShaderStorageBlockiv(program, block_index, GL_SHADER_STORAGE_BLOCK_DATA_SIZE)
    #         binding = glGetActiveShaderStorageBlockiv(program, block_index, GL_SHADER_STORAGE_BLOCK_BINDING)

    #         ssbo = glGenBuffers(1)
    #         glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo)
    #         glBufferData(GL_SHADER_STORAGE_BUFFER, block_size, None, GL_DYNAMIC_DRAW)
    #         glBindBufferBase(GL_SHADER_STORAGE_BUFFER, binding, ssbo)

    #         result[block_name] = StorageBlock(name=block_name, binding=binding, size=block_size, buffer_id=ssbo)

    #     return result

    @classmethod
    def reflect_instance_attributes(cls, program: int, location_map: dict[int, int], locations: list[int]) -> tuple[int, BufferLayout]:
        instance_vbo: int | None = None
        instance_buffer = None
        MAX_SPRITES = 32768

        count = gl.glGetProgramiv(program, gl.GL_ACTIVE_ATTRIBUTES) # type: ignore
        if count > 2:
            instance_attributes: list[Attribute] = []

            instance_vbo = gl.glGenBuffers(1) # type: ignore
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, instance_vbo) # type: ignore

            total_floats = 0
            for i in range(2, count):
                lookup_i = locations[i]
                loc_map = location_map.get(lookup_i)

                if loc_map is None:
                    ValueError(f"Atributo {i} não possui correspondente adequado.")
                    
                name, size, gl_type = gl.glGetActiveAttrib(program, loc_map)
                total_floats += cls._GL_TYPE_SIZES[gl_type]
                
            instance_stride = total_floats * 4

            gl.glBufferData(gl.GL_ARRAY_BUFFER, MAX_SPRITES * instance_stride, None, gl.GL_DYNAMIC_DRAW) # type: ignore
            
            offset = 0
            for i in range(2, count):
                lookup_i = locations[i]
                loc_map = location_map.get(lookup_i)

                name, size, gl_type = gl.glGetActiveAttrib(program, loc_map)
                name_str = name.decode()
                base_location = gl.glGetAttribLocation(program, name_str)
                
                floats = cls._GL_TYPE_SIZES[gl_type]
                instance_attributes.append(Attribute(name_str, base_location, size, floats, offset))

                if gl_type == gl.GL_FLOAT_MAT4: # type: ignore
                    for column in range(4):
                        curr_location = base_location + column
                        gl.glEnableVertexAttribArray(curr_location) # type: ignore
                        glAndPointerOffset = offset + (column * 16) # type: ignore
                        gl.glVertexAttribPointer(curr_location, 4, gl.GL_FLOAT, gl.GL_FALSE, instance_stride, ctypes.c_void_p(glAndPointerOffset)) # type: ignore
                        gl.glVertexAttribDivisor(curr_location, 1) # type: ignore
                else:
                    gl.glEnableVertexAttribArray(base_location) # type: ignore
                    gl.glVertexAttribPointer(base_location, floats, gl.GL_FLOAT, gl.GL_FALSE, instance_stride, ctypes.c_void_p(offset)) # type: ignore
                    gl.glVertexAttribDivisor(base_location, 1) # type: ignore

                offset += floats * 4
            
            instance_buffer = BufferLayout(instance_stride, instance_attributes)

        return instance_vbo, instance_buffer # type: ignore

    @classmethod
    def reflect_quad_attributes(cls, program: int, location_map: dict[int, int]) -> tuple[int, BufferLayout]:
        vertices = np.array([
            -0.5, -0.5,  0.0,   0,  0,
             0.5, -0.5,  0.0,   1,  0,
             0.5,  0.5,  0.0,   1,  1,
            -0.5,  0.5,  0.0,   0,  1,
        ], dtype=np.float32)

        quad_attributes: list[Attribute] = []

        quad_vbo = gl.glGenBuffers(1) # type: ignore
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, quad_vbo) # type: ignore
        vertex_stride = 5 * vertices.itemsize
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW) # type: ignore

        offset = 0
        for i in range(2):
            loc_map = location_map.get(i)
            if loc_map is None:
                raise ValueError(f"Atributo {i} não possui correspondente adequado.")
            name, size, gl_type = gl.glGetActiveAttrib(program, loc_map)
            name_str = name.decode()
            location = gl.glGetAttribLocation(program, name_str)
            floats = cls._GL_TYPE_SIZES[gl_type]
            quad_attributes.append(Attribute(name_str, location, size, floats, offset))
            gl.glEnableVertexAttribArray(location) # type: ignore
            gl.glVertexAttribPointer(location, floats, gl.GL_FLOAT, gl.GL_FALSE, vertex_stride, ctypes.c_void_p(offset)) # type: ignore
            gl.glVertexAttribDivisor(location, 0) # type: ignore

            offset += floats * 4

        quad_buffer = BufferLayout(vertex_stride, quad_attributes)
        return quad_vbo, quad_buffer # type: ignore

    @staticmethod
    def reflect_ebo() -> int:
        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)

        ebo = gl.glGenBuffers(1) # type: ignore
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ebo) # type: ignore
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW) # type: ignore

        return ebo # type: ignore

    @classmethod
    def build_buffers(cls, shader: Shader) -> object:
        program = shader.program
        gl.glUseProgram(program) # type: ignore

        vao = gl.glGenVertexArrays(1) # type: ignore
        gl.glBindVertexArray(vao) # type: ignore

        ebo = cls.reflect_ebo()

        location_map: dict[int, int] = {}
        locations: list[int] = []
        count: int = gl.glGetProgramiv(program, gl.GL_ACTIVE_ATTRIBUTES) # type: ignore
        for i in range(count):
            name, _, _ = gl.glGetActiveAttrib(program, i)
            name_str = name.decode()
            location = gl.glGetAttribLocation(program, name_str)
            location_map[location] = i
            locations.append(location)
        locations.sort()

        quad_vbo, quad_buffer = cls.reflect_quad_attributes(program, location_map)
        instance_vbo, instance_buffer = cls.reflect_instance_attributes(program, location_map, locations)
        ubos = cls.reflect_ubos(program)
        ssbos = {"a": StorageBlock("", -1, 0, -1)}#cls.reflect_ssbos(program)


        vertex_state = VertexArrayState(vao, quad_vbo, instance_vbo, ebo, quad_buffer, instance_buffer)
        resources = ShaderResources(ubos, ssbos)
        shader.set_state(vertex_state, resources)
        shader.built = True

        gl.glBindVertexArray(0) # type: ignore

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0) # type: ignore
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, 0) # type: ignore
        gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, 0) # type: ignore

    @classmethod
    def get_shader(cls, name: str) -> Shader:
        return cls._shaders[name]

    @staticmethod
    def compile_shader(vertex: str, fragment: str):
        shader = compileProgram(
            compileShader(vertex, gl.GL_VERTEX_SHADER), # type: ignore
            compileShader(fragment, gl.GL_FRAGMENT_SHADER), # type: ignore
            validate=False
        )
        return shader

    @classmethod
    def set_shader(cls, name: str) -> None:
        shader = cls.get_shader(name)
        gl.glUseProgram(shader.program) # type: ignore
        cls._current_program = shader
        
    @classmethod
    def get_current_shader(cls) -> Shader:
        return cls._current_program

    @classmethod
    def init_opengl(cls, size: tuple[int, int], flags: int, title: str, color: tuple[int, int, int, int]=(0, 0, 0, 255)) -> None:
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLEBUFFERS, 0)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, 0)

        pg.display.gl_set_attribute(pg.GL_ALPHA_SIZE, 8)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, 24)
        pg.display.set_mode(size, flags, vsync=1)
        pg.display.set_caption(title)

        width, height = size
        gl.glViewport(0, 0, width, height) # type: ignore
        gl.glDisable(gl.GL_MULTISAMPLE) # type: ignore
        
        r, g, b, a = color
        gl.glClearColor(r / 255, g / 255, b / 255, a / 255) # type: ignore

        gl.glEnable(gl.GL_BLEND) # type: ignore
        gl.glEnable(gl.GL_DEPTH_TEST) # type: ignore
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA) # type: ignore
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1) # type: ignore

class ShaderRender:
    _draw_calls: list[Sprite] = []
    _PROJECTIONS = {}
    _viewsize: tuple[int, int, int, int] = (0, 0, 0, 0)
    _fov = 70

    @classmethod
    def update_projections(cls, fov: float) -> None:
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT) # type: ignore
        x, y, width, height = viewport # type: ignore
        cls._viewsize = x, y, width, height # type: ignore
        cls._fov = fov

        cls._PROJECTIONS["perspective"] = glm.perspective( # type: ignore
            glm.radians(cls._fov), # type: ignore
            width / height,
            0.1,
            10000.0
        )
        cls._PROJECTIONS["orthogonal"] = glm.ortho( # type: ignore
            -width / 100, width / 100,
            -height / 100, height / 100,
            -100,
            100
        )

    @classmethod
    def add_draw_call(cls, sprite: Sprite) -> None:
        cls._draw_calls.append(sprite)

    @classmethod
    def render_batch(cls, texture: int, data: NDArray[np.uint8], count: int, view: np.ndarray, unit=gl.GL_TEXTURE0) -> None: # type: ignore
        shaders = ShaderManager.get_current_shader()
        ubo = shaders.resources.ubos["Camera"].buffer_id

        vao = shaders.vertex_state.vao
        gl.glBindVertexArray(vao) # type: ignore
        
        gl.glBindBuffer(gl.GL_UNIFORM_BUFFER, ubo) # type: ignore

        gl.glBufferSubData( # type: ignore
            gl.GL_UNIFORM_BUFFER, # type: ignore
            0,
            view.nbytes,
            view
        )
        # glBufferSubData(
        #     GL_UNIFORM_BUFFER,
        #     64,
        #     8,
        #     np.array([0, .2], dtype=np.float32)
        # )
        
        instance_vbo = shaders.vertex_state.instance_vbo
        if instance_vbo is not None:
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, instance_vbo) # type: ignore
            gl.glBufferSubData(gl.GL_ARRAY_BUFFER, 0, data.nbytes, data) # type: ignore
        
        gl.glActiveTexture(unit) # type: ignore
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture) # type: ignore

        # glEnable(GL_DEPTH_TEST)
        # glDepthMask(GL_TRUE)
        # glDisable(GL_BLEND)

        # glDepthMask(GL_FALSE)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, instance_vbo) # type: ignore

        gl.glDrawElementsInstanced(gl.GL_TRIANGLES, 6, gl.GL_UNSIGNED_INT, None, count) # type: ignore

    @staticmethod
    def euler_view_mat(pitch: float, yaw: float, roll: float):
        p_rad: int = glm.radians(pitch) # type: ignore
        y_rad: int = glm.radians(yaw) # type: ignore
        r_rad: int = glm.radians(roll) # type: ignore

        pitch_quat = glm.angleAxis(p_rad, glm.vec3(1.0, 0.0, 0.0)) # type: ignore
        yaw_quat = glm.angleAxis(y_rad, glm.vec3(0.0, 1.0, 0.0)) # type: ignore
        roll_quat = glm.angleAxis(r_rad, glm.vec3(0.0, 0.0, 1.0)) # type: ignore

        orientation = yaw_quat * pitch_quat * roll_quat
        
        rotation_matrix = glm.mat4(glm.mat3_cast(orientation)) # type: ignore

        return rotation_matrix

    @classmethod
    def render(cls) -> None:
        curr_camera = CameraManager.get_main_camera()
        camera_angle = (-curr_camera.angles[1], curr_camera.angles[0], curr_camera.angles[2])
        view = cls.euler_view_mat(*camera_angle)
        view = np.array(view, dtype=np.float32).flatten()
        
        viewport: tuple[int, int, int, int] = gl.glGetIntegerv(gl.GL_VIEWPORT) # type: ignore
        x, y, width, height = viewport # type: ignore
        if cls._viewsize != (x, y, width, height) or cls._fov != curr_camera.fov:
            cls.update_projections(curr_camera.fov)

        batch: list[Sprite] = []
        last_texture_id: int | float = float("-inf")
        last_unit: int | float = float("-inf")
        last_shader = "__def__"
        last_perspective = True

        for sprite in cls._draw_calls:
            same_sprite = sprite.texture_id == last_texture_id
            same_unit = sprite.unit == last_unit
            same_shader = sprite.shader == last_shader
            same_projection = sprite.perspective == last_perspective
            same_batch = same_sprite and same_unit and same_shader and same_projection

            if not same_batch and batch:
                data = cls.build_instance_buffer(batch)
                cls.render_batch(last_texture_id, data, len(batch), view, unit=last_unit) # type: ignore
                batch = []

            if not same_shader or ShaderManager.get_current_shader().name != sprite.shader:
                ShaderManager.set_shader(sprite.shader)

            batch.append(sprite)
            last_texture_id = sprite.texture_id
            last_unit = sprite.unit
            last_shader = sprite.shader
            last_perspective = sprite.perspective

        if batch:
            data = cls.build_instance_buffer(batch)
            cls.render_batch(last_texture_id, data, len(batch), view, unit=last_unit) # type: ignore

        cls._draw_calls = []

    @classmethod
    def build_instance_buffer(cls, sprites: list[Sprite]) -> NDArray[np.float32]:
        curr_camera = CameraManager.get_main_camera()
        shader = ShaderManager.get_current_shader()
        vertex_state = shader.vertex_state
        if vertex_state.instance_layout == None:
            instance_attributes = []
        else:
            instance_attributes = vertex_state.instance_layout.attributes
        data: list[int | float] = []

        for s in sprites:
            x, y, z = s.pos
            w, h, t = s.scale
            pitch, yaw, roll = s.rotation

            model = glm.mat4(1.0)

            model = glm.translate(model, glm.vec3(x, y, z)) # type: ignore
            model = glm.translate(model, glm.vec3(*(-curr_camera.pos))) # type: ignore
            model = glm.rotate(model, pitch, glm.vec3(1,0,0)) # type: ignore
            model = glm.rotate(model, yaw, glm.vec3(0,1,0)) # type: ignore
            model = glm.rotate(model, roll, glm.vec3(0,0,1)) # type: ignore
            model = glm.scale(model, glm.vec3(w, h, t)) # type: ignore

            projection = cls._PROJECTIONS["perspective"] if s.perspective else cls._PROJECTIONS["orthogonal"] # type: ignore
            
            u0 = s.uv.x / ShaderTexture.get_atlas_size()
            v0 = s.uv.y / ShaderTexture.get_atlas_size()
            us = s.uv.w / ShaderTexture.get_atlas_size() * 0.999
            vs = s.uv.h / ShaderTexture.get_atlas_size() * 0.999

            for attr in instance_attributes:
                if attr.name == "model":
                    for column in range(4):
                        data.extend(model[column])
                elif attr.name == "projection":
                    for column in range(4):
                        data.extend(projection[column])
                elif attr.name == "iUV":
                    data.extend([u0, v0, us, vs])
                else:
                    values = s.attrs[attr.name]
                    data.extend([*values])

        return np.array(data, dtype=np.float32)