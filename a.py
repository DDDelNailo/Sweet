import math
from pygame.locals import * # type: ignore
import sweet as sw
from sweet.vector import Vec3
from pathlib import Path

sw.Display.resizable(True)
screen_size = sw.Display.screen_size
sw.Display.size((screen_size[0], screen_size[1]))
sw.Display.background((135, 206, 250, 255))

sw.init()

CWD = Path.cwd()
sw.Resources.load_assets(CWD / "assets.json")
BUILD = CWD / "src" / "sweet" / "build"
panini = sw.Shader.add(BUILD / "__panini__.vsh", BUILD / "__panini__.fsh", "panini")
panini_program = panini.program
panini_fbo = sw.Shader.new_fbo(screen_size)

class test(sw.Entity):
    def __init__(self):
        #sw.Textures.get("player")
        super().__init__(None, (0, 0, 175), order=3, tick=True)
        self.pos: Vec3
        self.angle: Vec3
        self.camera_angle = Vec3(0, 0, 0)
        self.mouse_x, self.mouse_y = sw.inputting.Input.get_mouse_pos()
        self.perspective = True
        self.fov = 70
        self.speed = 5
        self.player_height = 1
        self.velocity = Vec3(0, 0, 0)
        sw.inputting.Input.set_mouse_visibility(False)
        self.a = Vec3(0, 0, 0)
        self.height = self.image.get_width(), self.image.get_height()

    def tick(self):
        # direction = self.camera_angle.direction() * self.speed
        self.velocity.y -= .5
        self.pos += self.velocity

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.W):
            self.pos.x -= math.sin(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z -= math.cos(math.radians(self.camera_angle.x)) * self.speed
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.S):
            self.pos.x += math.sin(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z += math.cos(math.radians(self.camera_angle.x)) * self.speed
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.A):
            self.pos.x -= math.cos(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z += math.sin(math.radians(self.camera_angle.x)) * self.speed
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.D):
            self.pos.x += math.cos(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z -= math.sin(math.radians(self.camera_angle.x)) * self.speed
        self.pos.y = max(self.pos.y, self.player_height)
        if sw.inputting.Input.get_pressed(sw.inputting.Input.key_code.SPACE) and self.pos.y <= self.player_height:
            self.velocity.y = 20

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.I):
            self.a.y -= 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.J):
            self.a.x -= 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.K):
            self.a.y += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.L):
            self.a.x += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.N):
            self.a.z += 1
        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.M):
            self.a.z -= 1

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.TAB):
            self.perspective = not self.perspective

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.Q):
            self.fov += 1

        if sw.inputting.Input.get_press(sw.inputting.Input.key_code.E):
            self.fov -= 1

        main_cam = sw.camera.CameraManager.get_main_camera()
        main_cam.pos = Vec3(self.pos.x, self.pos.y, self.pos.z)
        main_cam.fov = self.fov

        mouse_x, mouse_y = sw.inputting.Input.get_mouse_pos()
        mouse_dx = mouse_x - self.mouse_x
        mouse_dy = mouse_y - self.mouse_y
        self.mouse_x, self.mouse_y = mouse_x, mouse_y
        
        self.camera_angle.x -= mouse_dx * .2
        self.camera_angle.y += mouse_dy * .2
        self.camera_angle.y = min(90, max(-90, self.camera_angle.y))

        # self.camera_angle = Vec3(0, 0, 0)
        main_cam.angles = self.camera_angle

        if self.mouse_x == 0 or self.mouse_x == screen_size[0] - 1:
            sw.inputting.Input.set_mouse_pos(screen_size[0] // 2, self.mouse_y)
            self.mouse_x = screen_size[0] // 2
        if self.mouse_y == 0 or self.mouse_y == screen_size[1] - 1:
            sw.inputting.Input.set_mouse_pos(self.mouse_x, screen_size[1] // 2)
            self.mouse_y = screen_size[1] // 2

    def draw(self):
        # pillar = sw.Textures.get("pillar")
        front_pillar = sw.Resources.texture("plane")
        plane = sw.Resources.model("aviao")
        outro = sw.Resources.model("__quad__")
        # sw.entity.Draw.draw_image(floor, Vec3(0, 0, floor.get_height() // 2), Vec3(floor.get_width(), floor.get_height(), 1), Vec3(90, 0, 0), perspective=self.perspective)
        # for i in range(0, 1):
        #     sw.entity.Draw.draw_image(wall, Vec3(wall.get_width() * i, wall.get_height() // 2, 0), Vec3(wall.get_width(), wall.get_height(), 1), self.angle, perspective=self.perspective)
        # for i in range(0, 1):
        #     sw.entity.Draw.draw_image(pillar, Vec3(pillar.get_width() * i, pillar.get_height() // 2, 50), Vec3(pillar.get_width(), pillar.get_height(), 1), self.angle, perspective=self.perspective)
        sw.Shader.use("__def__")

        # sw.Shader.use_frame(panini_fbo, clear_color=(1, 0, 0, 1))
        main_cam = sw.camera.CameraManager.get_main_camera()
        sw.Shader.ubo(0, "uCamPos", "3f", *(main_cam.pos.unp()))
        sw.entity.Draw.draw_image(plane, front_pillar, Vec3(self.a.x, self.a.y, self.a.z), Vec3(1, 1, 1), self.angle, perspective=self.perspective)
        # sw.Shader.force_draw()

        # sw.Shader.use("panini")
        # sw.Shader.use_frame(None, False, (0, .5, 0, 1))
        # panini_fbo.use()

        sw.entity.Draw.draw_image(outro, None, self.pos + Vec3(0, 0, -100), Vec3(100, 100, 100), self.angle, perspective=self.perspective)

test()
# # sw.Scene.create(test)
sw.run()
