from ..common import Draw, ConvertType, Rec, UVLocation, Sprite
import pygame as pg
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import glm
import numpy as np
from math import sin, cos, radians
from typing import Callable, Sequence
import uuid
from PIL import Image
from dataclasses import dataclass, field

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

    members: list[UniformMember] = field(default_factory=list)

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
    def __init__(self, width, height, occupation, padding=0) -> None:
        self.occupation = occupation
        self.width = width
        self.height = height
        self.padding = padding

        self.image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        initial = Rec(0, 0, width, height)
        self.free_rects = {(initial.x, initial.y, initial.w, initial.h): initial}
        self.used_rects = {}

    def insert(self, w, h) -> "Rec":
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

    def _place(self, rect):
        new_free = []

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

    def _intersect(self, a, b):
        return not (
            a.x >= b.x + b.w or
            a.x + a.w <= b.x or
            a.y >= b.y + b.h or
            a.y + a.h <= b.y
        )

    def _contains(self, a, b):
        return (
            a.x <= b.x and
            a.y <= b.y and
            a.x + a.w >= b.x + b.w and
            a.y + a.h >= b.y + b.h
        )

    def _prune(self, rects):
        pruned = []
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

    def _try_merge(self, a: "Rec", b: "Rec") -> "Rec":
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
    _atlas_loc: dict[Atlas] = {}
    _occupated_textures: dict[str] = {}

    @classmethod
    def new_atlas(cls) -> None:
        atlas = Atlas(cls._atlas_size, cls._atlas_size, uuid.uuid4().hex)
        location = cls.create_texture(atlas.image, ConvertType.IMAGE, atlas.occupation)
        atlas.tex_id = location.tex_id
        cls._atlas_array.append(atlas)
        cls._atlas_loc[location.tex_id] = atlas

    @classmethod
    def get_current_atlas(cls, width: int, height: int) -> Sequence[Atlas | Rec]:
        for atlas in cls._atlas_array:
            rect = atlas.insert(width, height)
            if not rect == None:
                return atlas, rect

        cls.new_atlas()
        atlas = cls._atlas_array[-1]
        rect = atlas.insert(width, height)

        return atlas, rect

    @classmethod
    def get_atlas(cls, tex_id: int) -> Atlas:
        return cls._atlas_loc[tex_id]

    @classmethod
    def texture_to_bytes(cls, texture: Draw, convert_type: ConvertType) -> Draw:
        if convert_type == ConvertType.VIDEO:
            return cls._video_to_bytes(texture)
        elif convert_type == ConvertType.GIF:
            return cls._gif_to_bytes(texture)
        elif convert_type == ConvertType.IMAGE:
            return cls._image_to_bytes(texture)

    @staticmethod
    def _image_to_bytes(texture: Draw) -> Draw:
        texture = texture.convert("RGBA")
        width, height = texture.size
        texture = texture.tobytes()
        return texture, width, height, GL_RGBA
    
    @staticmethod
    def _gif_to_bytes(texture: Draw) -> Draw:
        height, width = texture.shape[:2]

        if texture.shape[2] == 3:
            image_format = GL_RGB
        else:
            image_format = GL_RGBA

        texture = np.ascontiguousarray(texture)

        return texture, width, height, image_format

    @staticmethod
    def _video_to_bytes(texture: Draw) -> Draw:
        height, width = texture.shape[:2]
        texture = np.ascontiguousarray(texture)
        return texture, width, height, GL_BGR

    @classmethod
    def create_texture_atlas_list(cls, frames: Sequence[Draw], convert_type: ConvertType, location: list[UVLocation]) -> UVLocation:
        uv_list = []
        for i, frame in enumerate(frames):
            if len(location) == 0:
                loc = UVLocation("", None)
            else:
                loc = location[i]
                
            uv = cls.add_texture_atlas(frame, convert_type, loc)
            uv_list.append(uv)

        return uv_list

    @classmethod
    def update_texture_atlas_list(cls, frames: Sequence[Draw], convert_type: ConvertType, location: list[UVLocation]) -> None:
        for i, frame in enumerate(frames):
            cls.update_texture_atlas(frame, convert_type, location[i])

    @classmethod
    def delete_texture_atlas_list(cls, location: list[UVLocation]) -> None:
        for loc in location:
            cls.delete_texture_atlas(loc)

    @classmethod
    def create_texture_atlas(cls, texture: Draw, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)

        if location.tex_id:
            key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)
            atlas = cls.get_atlas(location.tex_id)

            if not atlas.used_rects.get(key) == None:
                if not width == location.uv.w or not height == location.uv.h:
                    raise ValueError("Tamanhos não batem")
                cls.update_texture_atlas(texture, convert_type, location)
                return location

        current_atlas, rect = cls.get_current_atlas(width, height)

        glBindTexture(GL_TEXTURE_2D, current_atlas.tex_id)
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            rect.x, rect.y,
            rect.w, rect.h,
            image_format,
            GL_UNSIGNED_BYTE,
            image
        )
        return UVLocation(current_atlas.tex_id, rect)

    @classmethod
    def update_texture_atlas(cls, texture: Draw, convert_type: ConvertType, location: UVLocation) -> UVLocation:
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)
        glBindTexture(GL_TEXTURE_2D, location.tex_id)
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            location.uv.x, location.uv.y,
            location.uv.w, location.uv.h,
            image_format,
            GL_UNSIGNED_BYTE,
            image
        )

    @classmethod
    def delete_texture_atlas(cls, location: UVLocation) -> None:
        key = (location.uv.x, location.uv.y, location.uv.w, location.uv.h)

        atlas = cls.get_atlas_id(location.tex_id)
        if not atlas.used_rects.get(key) == None:
            atlas.remove(location.uv)

            if len(atlas.used_rects) == 0 and len(cls._atlas_array) >= 2:
                ShaderManager.delete_texture(atlas.occupation)
                del cls._atlas_loc[atlas.tex_id]
                cls._atlas_array.remove(atlas)

    @classmethod
    def create_texture(cls, texture: Draw, convert_type: ConvertType, occupation: str=None) -> tuple:
        if occupation == None:
            occupation = uuid.uuid4().hex
            
        if not cls._occupated_textures.get(occupation) == None:
            tex_id = cls._occupated_textures[occupation]
            width, height = cls.update_texture(tex_id, texture, convert_type)

            return UVLocation(tex_id, Rec(x=0, y=0, w=width, h=height))
            
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)
        tex_id = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width,
            height,
            0,
            image_format,
            GL_UNSIGNED_BYTE,
            image)

        cls._occupated_textures[occupation] = tex_id
        return UVLocation(tex_id, uv=Rec(x=0, y=0, w=width, h=height))
    
    @classmethod
    def update_texture(cls, tex_id: int, texture: Draw, convert_type: ConvertType) -> int:
        glBindTexture(GL_TEXTURE_2D, tex_id)
        image, width, height, image_format = cls.texture_to_bytes(texture, convert_type)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width, height,
            0,
            image_format,
            GL_UNSIGNED_BYTE,
            image
        )

        return width, height
    
    @classmethod
    def delete_texture(cls, occupation: str) -> None:
        glDeleteTextures([cls._occupated_textures[occupation]])
        cls._occupated_textures.pop(occupation)

    @classmethod
    def get_texture_id(cls, occupation: str) -> int:
        return cls._occupated_textures[occupation]
    
class Shader:
    def __init__(self, vertex: str, fragment: str) -> None:
        self.vertex = vertex
        self.fragment = fragment

    def set_state(self, vertex_state, resources) -> None:
        self.vertex_state = vertex_state
        self.resources = resources

    def set_uniforms(self, uniforms):
        self.uniforms = uniforms

    def set_program(self, program):
        self.program = program

class ShaderManager:
    _current_program: str = None
    _UNIFORM_FUNCS: dict[Callable] = {
        "1i": glUniform1i,
        "2i": glUniform2i,
        "3i": glUniform3i,
        "4i": glUniform4i,
        "1f": glUniform1f,
        "2f": glUniform2f,
        "3f": glUniform3f,
        "4f": glUniform4f,
        "1fv": glUniform1fv,
        "2fv": glUniform2fv,
        "3fv": glUniform3fv,
        "4fv": glUniform4fv
    }

    _GL_TYPE_SIZES = {
        GL_FLOAT: 1,
        GL_FLOAT_VEC2: 2,
        GL_FLOAT_VEC3: 3,
        GL_FLOAT_VEC4: 4,

        GL_INT: 1,
        GL_INT_VEC2: 2,
        GL_INT_VEC3: 3,
        GL_INT_VEC4: 4,

        GL_FLOAT_MAT4: 16,
    }
    _shaders: dict[Shader] = {}
    
    @classmethod
    def _get_uniform_function(cls, data_type: str) -> Callable:
        return cls._UNIFORM_FUNCS[data_type]

    @classmethod
    def set_uniform_value(cls, uniform: str, data_type: str, *value: list) -> None:
        u = glGetUniformLocation(cls.get_current_shader().program, uniform)
        func = cls._get_uniform_function(data_type)
        value = list(value)
        params = [u] + value
        func(*params)

    @classmethod
    def add_shader(cls, name, path_vertex, path_fragment) -> None:
        with open(path_vertex, "r") as file:
            VERTEX_SHADER = file.read()
        with open(path_fragment, "r") as file:
            FRAGMENT_SHADER = file.read()

        cls._shaders[name] = Shader(vertex=VERTEX_SHADER, fragment=FRAGMENT_SHADER)

    @classmethod
    def get_shader(cls, name: str) -> Shader:
        return cls._shaders[name]

    @classmethod
    def build_shaders(cls) -> None:
        for shader in cls._shaders.values():
            vertex, fragment = shader.vertex, shader.fragment
            shader.set_program(cls.compile_shader(vertex, fragment))
            cls.build_buffers(shader)

    @classmethod
    def reflect_ubos(cls, shader: Shader) -> dict[str, UniformBlock]:
        program = shader.program

        result = {}

        block_count = glGetProgramiv(program, GL_ACTIVE_UNIFORM_BLOCKS)

        for block_index in range(block_count):

            length = ctypes.c_int()
            glGetActiveUniformBlockiv(program, block_index, GL_UNIFORM_BLOCK_NAME_LENGTH, length)
            name_length = length.value

            block_name = glGetActiveUniformBlockName(program, block_index, name_length)
            block_name = bytes(block_name[1][:-1])

            size = ctypes.c_int()
            glGetActiveUniformBlockiv(program, block_index, GL_UNIFORM_BLOCK_DATA_SIZE, size)
            block_size = size.value

            bind = ctypes.c_int()
            glGetActiveUniformBlockiv(program, block_index, GL_UNIFORM_BLOCK_BINDING, bind)
            binding = bind.value
            
            # indices = ctypes.c_int()
            # glGetActiveUniformBlockiv(program, block_index, GL_UNIFORM_BLOCK_ACTIVE_UNIFORM_INDICES, indices)
            # uniform_indices = indices.value

            count = ctypes.c_int()
            glGetActiveUniformBlockiv(program, block_index, GL_UNIFORM_BLOCK_ACTIVE_UNIFORMS, count)
            uniform_count = count.value

            indices = (GLuint * uniform_count)()
            glGetActiveUniformBlockiv(program, block_index, GL_UNIFORM_BLOCK_ACTIVE_UNIFORM_INDICES, indices)
            uniform_indices = list(indices)

            if isinstance(uniform_indices, int):
                uniform_indices = [uniform_indices]

            block = UniformBlock(name=block_name, index=block_index, binding=binding, data_size=block_size,)

            for uniform_index in uniform_indices:
                name, size, gl_type = glGetActiveUniform(program, uniform_index)
                indices = [uniform_index]
                params = (ctypes.c_int * 1)()
                glGetActiveUniformsiv(program, 1, indices, GL_UNIFORM_OFFSET, params)
                offset = params[0]

                params = (ctypes.c_int * 1)()
                glGetActiveUniformsiv(program, 1, indices, GL_UNIFORM_ARRAY_STRIDE, params)
                array_stride = params[0]

                params = (ctypes.c_int * 1)()
                glGetActiveUniformsiv(program, 1, indices, GL_UNIFORM_MATRIX_STRIDE, params)
                matrix_stride = params[0]

                member = UniformMember(
                    name=name,
                    gl_type=cls._GL_TYPE_SIZES[gl_type],
                    size=size,
                    offset=offset,
                    array_stride=array_stride,
                    matrix_stride=matrix_stride,
                )

                block.members.append(member)

            ubo = glGenBuffers(1)
            glBindBuffer(GL_UNIFORM_BUFFER, ubo)
            glBufferData(GL_UNIFORM_BUFFER, block.data_size, None, GL_DYNAMIC_DRAW)
            glBindBufferBase(GL_UNIFORM_BUFFER, block.binding, ubo)

            block.buffer_id = ubo

            result[block.name] = block

        return result

    @staticmethod
    def reflect_ssbos(shader: Shader) -> dict[str, StorageBlock]:
        program = shader.program

        result = {}

        block_count = glGetProgramiv(program, GL_SHADER_STORAGE_BLOCKS)

        for block_index in range(block_count):
            block_name = glGetActiveShaderStorageBlockName(program, block_index)
            block_size = glGetActiveShaderStorageBlockiv(program, block_index, GL_SHADER_STORAGE_BLOCK_DATA_SIZE)
            binding = glGetActiveShaderStorageBlockiv(program, block_index, GL_SHADER_STORAGE_BLOCK_BINDING)

            ssbo = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, ssbo)
            glBufferData(GL_SHADER_STORAGE_BUFFER, block_size, None, GL_DYNAMIC_DRAW)
            glBindBufferBase(GL_SHADER_STORAGE_BUFFER, binding, ssbo)

            result[block_name] = StorageBlock(name=block_name, binding=binding, size=block_size, buffer_id=ssbo)

        return result

    @classmethod
    def reflect_instance_attributes(cls, shader: Shader) -> dict[str, Attribute]:
        program = shader.program

        instance_vbo = None

        MAX_SPRITES = 32768

        count = glGetProgramiv(program, GL_ACTIVE_ATTRIBUTES)
        if count > 2:
            instance_attributes = []

            instance_vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)
            instance_stride = sum(cls._GL_TYPE_SIZES[gl_type] for _, _, gl_type in (glGetActiveAttrib(program, i) for i in range(2, count))) * 4
            glBufferData(GL_ARRAY_BUFFER, MAX_SPRITES * instance_stride * 4, None, GL_DYNAMIC_DRAW)
            
            offset = 0
            for i in range(2, count):
                name, size, gl_type = glGetActiveAttrib(program, i)
                floats = cls._GL_TYPE_SIZES[gl_type]
                instance_attributes.append(Attribute(name, i, size, floats, offset))

                if gl_type == GL_FLOAT_MAT4:
                    for column in range(4):
                        location = i + column
                        glEnableVertexAttribArray(location)
                        glVertexAttribPointer(location, 4, GL_FLOAT, GL_FALSE, instance_stride, ctypes.c_void_p(offset + column * 16))
                        glVertexAttribDivisor(location, 1)
                else:
                    glEnableVertexAttribArray(i)
                    glVertexAttribPointer(i, floats, GL_FLOAT, GL_FALSE, instance_stride, ctypes.c_void_p(offset))
                    glVertexAttribDivisor(i, 1)

                offset += floats * 4
            
            instance_buffer = BufferLayout(instance_attributes, instance_stride)

        return instance_vbo, instance_buffer

    @classmethod
    def reflect_quad_attributes(cls, shader: Shader) -> dict[str, Attribute]:
        vertices = np.array([
            -0.5, -0.5,  0.0,   0,  0,
             0.5, -0.5,  0.0,   1,  0,
             0.5,  0.5,  0.0,   1,  1,
            -0.5,  0.5,  0.0,   0,  1,
        ], dtype=np.float32)

        program = shader.program
        quad_attributes = []

        quad_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, quad_vbo)
        vertex_stride = 5 * vertices.itemsize
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

        offset = 0
        for i in range(2):
            name, size, gl_type = glGetActiveAttrib(program, i)
            floats = cls._GL_TYPE_SIZES[gl_type]
            quad_attributes.append(Attribute(name, i, size, floats, offset))
            glEnableVertexAttribArray(i)
            glVertexAttribPointer(i, floats, GL_FLOAT, GL_FALSE, vertex_stride, ctypes.c_void_p(offset))

            offset += floats * 4

        quad_buffer = BufferLayout(quad_attributes, vertex_stride)
        return quad_vbo, quad_buffer

    @staticmethod
    def reflect_ebo() -> int:
        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)

        ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

        return ebo

    @classmethod
    def build_buffers(cls, shader: Shader) -> object:
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        ebo = cls.reflect_ebo()
        quad_vbo, quad_buffer = cls.reflect_quad_attributes(shader)
        instance_vbo, instance_buffer = cls.reflect_instance_attributes(shader)
        ubos = cls.reflect_ubos(shader)
        ssbos = None#cls.reflect_ssbos(shader)

        glBindVertexArray(0)

        vertex_state = VertexArrayState(vao, quad_vbo, instance_vbo, ebo, quad_buffer, instance_buffer)
        resources = ShaderResources(ubos, ssbos)
        shader.set_state(vertex_state, resources)

    @classmethod
    def get_shader(cls, name: str) -> Shader:
        return cls._shaders[name]

    @staticmethod
    def compile_shader(vertex: str, fragment: str) -> Callable:
        shader = compileProgram(
            compileShader(vertex, GL_VERTEX_SHADER),
            compileShader(fragment, GL_FRAGMENT_SHADER),
            validate=False
        )
        return shader

    @classmethod
    def set_shader(cls, name: str) -> None:
        shader = cls.get_shader(name)
        glUseProgram(shader.program)
        cls._current_program = shader
        
    @classmethod
    def get_current_shader(cls) -> Shader:
        return cls._current_program

    @classmethod
    def init_opengl(cls, size: tuple, flags: int, title: str, color: tuple=(0, 0, 0, 255)) -> None:
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLEBUFFERS, 0)
        pg.display.gl_set_attribute(pg.GL_MULTISAMPLESAMPLES, 0)

        pg.display.gl_set_attribute(pg.GL_ALPHA_SIZE, 8)
        pg.display.gl_set_attribute(pg.GL_DEPTH_SIZE, 24)
        pg.display.set_mode(size, flags)
        pg.display.set_caption(title)

        width, height = size
        glViewport(0, 0, width, height)
        glDisable(GL_MULTISAMPLE)
        
        r, g, b, a = color
        glClearColor(r / 255, g / 255, b / 255, a / 255)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

class ShaderRender:
    _draw_calls: list[Sprite] = []
    @classmethod
    def add_draw_call(cls, sprite: Sprite) -> None:
        cls._draw_calls.append(sprite)

    @classmethod
    def render_batch(cls, texture: Draw, data: np.array, view: np.ndarray, unit=GL_TEXTURE0) -> None:
        shaders = ShaderManager.get_current_shader()
        ubo = shaders.resources.ubos["Camera"].buffer_id
        glBindBuffer(GL_UNIFORM_BUFFER, ubo)
        glBufferSubData(
            GL_UNIFORM_BUFFER,
            64,
            view.nbytes,
            view
        )
        
        instance_vbo = shaders.vertex_state.instance_vbo
        glBindBuffer(GL_ARRAY_BUFFER, instance_vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, data.nbytes, data)
        
        glActiveTexture(unit)
        glBindTexture(GL_TEXTURE_2D, texture)

        vao = shaders.vertex_state.vao
        glBindVertexArray(vao)
        instance_stride = shaders.vertex_state.instance_layout.stride

        instance_count = len(data) // (instance_stride // 4)
        glDrawElementsInstanced(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None, instance_count)

    @classmethod
    def render(cls) -> None:
        # perspective = glm.ortho(0, cls.screen_size[0], cls.screen_size[1], 0, -100, 100)
        perspective = glm.perspective(
            glm.radians(70.0),
            cls.screen_size[1] / cls.screen_size[0],
            0.1,
            1000.0
        )
        view = glm.lookAt(
            glm.vec3(0, 0, 5),
            glm.vec3(0, 0, 0),
            glm.vec3(0, 1, 0)
        )
        projection = perspective
        # cam = Camera.get_main_camera()
        # cam_pos = cam.get_pos()
        # cam_scale = cam.get_scale()
        # cam_angle = cam.get_angle()
        # view = cls.build_view(cam_pos, cam_angle, cam_scale, (cam_scale[0] * cls.screen_size[0] / 2, cam_scale[1] * cls.screen_size[1] / 2))
        
        batch = []
        last_texture_id = float("-inf")
        last_unit = float("-inf")
        last_program = "def"

        for sprite in cls._draw_calls:
            same_sprite = sprite.texture_id == last_texture_id
            same_unit = sprite.unit == last_unit
            same_program = sprite.program == last_program
            same_batch = same_sprite and same_unit and same_program

            if not same_batch and batch:
                data = cls.build_instance_buffer(batch)

                if not same_program and not batch[0].program == "def":
                    ShaderManager.set_shader(batch[0].program)

                cls.render_batch(last_texture_id, data, view, unit=last_unit)

                batch = []

            batch.append(sprite)
            last_texture_id = sprite.texture_id
            last_unit = sprite.unit
            last_program = sprite.program

        if batch:
            data = cls.build_instance_buffer(batch)

            if not same_program and not batch[0].program == "def":
                ShaderManager.set_shader(batch[0].program)

            cls.render_batch(last_texture_id, data, view, unit=last_unit)

        cls._draw_calls = []

    @classmethod
    def build_instance_buffer(cls, sprites) -> np.array:
        data = []

        for s in sprites:
            x, y, z = s.pos
            w, h, t = s.scale
            pitch, yaw, roll = s.rotation

            model = glm.mat4(1.0)

            model = glm.translate(model, glm.vec3(x, y, z))
            model = glm.rotate(model, pitch, glm.vec3(1,0,0))
            model = glm.rotate(model, yaw, glm.vec3(0,1,0))
            model = glm.rotate(model, roll, glm.vec3(0,0,1))
            model = glm.scale(model, glm.vec3(w, h, t))
            
            u0 = s.uv.x / cls._atlas_size
            v0 = s.uv.y / cls._atlas_size
            us = s.uv.w / cls._atlas_size
            vs = s.uv.h / cls._atlas_size

            o_x, o_y = s.offset

            data.extend([
                x, y, z,
                w, h, t,
                yaw, pitch, roll,
                o_x, o_y,
                u0, v0,
                us, vs,
                ShaderManager.screen_size[0],
                ShaderManager.screen_size[1],
            ])
            data.extend(s.overhead)

        return np.array(data, dtype=np.float32)

    # @classmethod
    # def build_instance_buffer(cls, sprites, view_matrix, cam_scale, cam_angle) -> np.array:
    #     data = []

    #     cls.set_shader(sprites[0].program)

    #     for s in sprites:
    #         x, y = s.pos
    #         w, h = s.scale
    #         rotation = s.rotation

    #         if not s.static:
    #             pos = np.array([x, y, 0.0, 1.0], dtype=np.float32)
    #             transformed = view_matrix @ pos
    #             x, y = transformed[0], transformed[1]

    #             w /= cam_scale[0]
    #             h /= cam_scale[1]
    #             rotation -= cam_angle

    #         cos_r = cos(radians(rotation))
    #         sin_r = sin(radians(rotation))

    #         u0 = s.uv.x / cls._atlas_size
    #         v0 = s.uv.y / cls._atlas_size
    #         us = s.uv.w / cls._atlas_size
    #         vs = s.uv.h / cls._atlas_size

    #         data.extend([
    #             x, y,
    #             w, h,
    #             cos_r, sin_r,
    #             u0, v0,
    #             us, vs,
    #         ])
    #         data.extend(s.overhead)

    #     return np.array(data, dtype=np.float32)
