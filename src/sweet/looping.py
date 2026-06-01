import pygame as pg
from .common import Drawing
from pygame.locals import *
import os
from .graphics.shaders import ShaderManager, ShaderRender
from OpenGL.GL import *
from .entity import EntityManager
from .inputting import Input
from .testing import Testing
from pathlib import Path

class GameLoop:
    pg.init()
    _title: str = "[No Title]"
    _screen_size: tuple = (100, 100)
    _non_full_screen_size: tuple = (100, 100)
    _color: tuple = (0, 0, 0, 0)
    fps: int = 60
    _info = pg.display.Info()
    view_width: int = _info.current_w
    view_height: int = _info.current_h
    _fullscreen: bool = False
    _resizable: bool = False
    _fullscreenable: bool = False
    _flags: int = DOUBLEBUF | OPENGL
    _built = False
    debug: bool = False
    debug_time: bool = False

    @classmethod
    def set_can_fullscreen(cls, value: bool) -> None:
        cls._fullscreenable = value

    @classmethod
    def get_can_fullscreen(cls) -> bool:
        return cls._fullscreenable

    @classmethod
    def get_fullscreen(cls) -> bool:
        return cls._fullscreen
    
    @staticmethod
    def set_icon(icon: Drawing) -> None:
        data = icon.tobytes()
        surface = pg.image.fromstring(data, icon.size, icon.mode)
        pg.display.set_icon(surface.convert())

    @classmethod
    def set_fullscreen(cls, value: bool) -> None:
        cls._fullscreen = value
        if cls._fullscreen:
            cls._screen_size = (cls.view_width, cls.view_height)

    @classmethod
    def set_resizable(cls, value: bool) -> None:
        cls._resizable = value

        cls._flags = DOUBLEBUF | OPENGL
        if cls._resizable:
            cls._flags = DOUBLEBUF | OPENGL | pg.RESIZABLE

    @classmethod
    def get_resizable(cls) -> bool:
        return cls._resizable

    @classmethod
    def set_title(cls, title: str) -> None:
        cls._title = title

    @classmethod
    def set_fps(cls, fps: int) -> None:
        cls._fps = fps

    @classmethod
    def get_fps(cls) -> int:
        return cls._fps

    @classmethod
    def get_title(cls) -> str:
        return cls._title

    @classmethod
    def set_background_color(cls, color: tuple) -> None:
        if cls._built:
            glClearColor(*map(lambda x: x / 255, color))
        cls._color = color

    @classmethod
    def get_background_color(cls) -> tuple:
        return cls._color

    @classmethod
    def set_screen_size(cls, size: tuple) -> None:
        if not cls.get_fullscreen():
            cls._screen_size = size
        if size == (cls.view_width, cls.view_height):
            cls.set_fullscreen(True)

    @classmethod
    def get_screen_size(cls) -> tuple:
        return cls._screen_size
    
    @classmethod
    def init(cls) -> None:
        ShaderManager.init_opengl(cls.get_screen_size(), cls._flags, cls._title, cls._color)
        BASE_DIR = Path(__file__).resolve().parent
        BUILD = BASE_DIR / "build"
        ShaderManager.add_shader("a", BUILD / "__sh__.vsh", BUILD / "__sh__.fsh")
        ShaderManager.add_shader("b", BUILD / "__sh__.vsh", BUILD / "__sh__.fsh")
        ShaderManager.add_shader("__def__", BUILD / "__sh__.vsh", BUILD / "__sh__.fsh")
        # ShaderManager.build_shaders()
        ShaderManager.set_shader("__def__")
        cls._built = True

    @classmethod
    def end(cls) -> None:
        cls._running = False

    @classmethod
    def start(cls) -> None:
        cls._fps = 60
        clock = pg.time.Clock()
        cls._running = True

        while cls._running:
            Input.update()

            Input.mouse_scroll_x = 0
            Input.mouse_scroll_y = 0
            for event in pg.event.get():
                mods = pg.key.get_mods()
                if mods & pg.KMOD_CAPS:
                    Input.set_caps(True)
                else:
                    Input.set_caps(False)
                if event.type == pg.QUIT:
                    cls._running = False

                if event.type == pg.MOUSEWHEEL:
                    Input.mouse_scroll_x = event.x
                    Input.mouse_scroll_y = event.y

                if event.type == pg.WINDOWFOCUSLOST:
                    Input.set_focus(False)

                if event.type == pg.WINDOWFOCUSGAINED:
                    Input.set_focus(True)

                if cls.get_resizable():
                    if event.type == pg.VIDEORESIZE:
                        GameLoop.set_screen_size((event.w, event.h))

                if cls.get_can_fullscreen():
                    if event.type == pg.KEYDOWN and event.key == pg.K_F11:
                        cls.set_fullscreen(not cls.get_fullscreen())

                        if not cls.get_fullscreen():
                            max_value = (cls.view_width, cls.view_height)
                            screen_value = cls.get_screen_size()
                            screen_value = (min(screen_value[0], max_value[0] - 30), min(screen_value[1], max_value[1] - 80))
                            os.environ['SDL_VIDEO_CENTERED'] = "1"
                            pg.display.set_mode(max_value, cls.get_flags())
                            pg.display.set_mode(screen_value, cls.get_flags())
                            cls.update_screen_size(screen_value)
                        else:
                            screen_value = (cls.view_width, cls.view_height)
                            pg.display.set_mode(screen_value, pg.FULLSCREEN | cls.get_flags())
                            cls.update_screen_size(screen_value)

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            # if not ShaderManager.get_current_shader() == "__def__":
            #     ShaderManager.set_shader("__def__")
            #     ShaderManager.set_uniform_value("u_texture", "1i", 0)

            if cls.debug:
                Testing.cummulation_start()

            entities = EntityManager.get_tick_entities(0)
            for entity in entities:
                entities[entity].pre_tick()
            entities = EntityManager.get_tick_entities(1)
            for entity in entities:
                entities[entity].tick()
            entities = EntityManager.get_tick_entities(2)
            for entity in entities:
                entities[entity].pos_tick()
                
            entities = EntityManager.get_all_entities()
            for order in entities.values():
                for layer in order.values():
                    for entity in layer:
                        entity.draw()

            ShaderRender.render()
                        
            order_changes: list = EntityManager.get_order_changes()
            for key in order_changes:
                EntityManager.set_order_change(*order_changes[key])

            layer_changes: list = EntityManager.get_layer_changes()
            for key in layer_changes:
                EntityManager.set_layer_change(*layer_changes[key])

            entity_changes: list = EntityManager.get_entity_changes()
            for key in entity_changes:
                EntityManager.create_entity(*entity_changes[key])

            destroy_changes: list = EntityManager.get_destroy_changes()
            for key in destroy_changes:
                EntityManager.destroy_entity(entity_changes[key])

            EntityManager.clear_agend()

            if cls.debug:
                Testing.cummulation_end()

            pg.display.flip()
            clock.tick(cls.get_fps())

if __name__ == "__main__":
    GameLoop.start()