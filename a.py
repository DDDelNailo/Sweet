import math

import pygame
from pygame.locals import *
import sweet as sw
from pathlib import Path
from sweet.vector import Vec3, Vec2

sw.Display.resizable(True)
screen_size = sw.Display.screen_size
sw.Display.size((screen_size[0], screen_size[1]))
sw.Display.background((255, 230, 147, 255))

sw.init()

CWD = Path.cwd()
sw.Textures.load_json_resource(CWD / "images.json")

class test(sw.Entity):
    def __init__(self):
        super().__init__(sw.Textures.get("player"), (0, 0, 175), order=3, tick=True)
        self.camera_angle = Vec3(0, 0, 0)
        self.mouse_x, self.mouse_y = sw.inputting.Input.get_mouse_pos()
        self.perspective = True
        self.fov = 70
        self.speed = 5
        self.velocity = Vec3(0, 0, 0)
        sw.inputting.Input.set_mouse_visibility(False)
        self.width, self.height = self.image.get_width(), self.image.get_height()

    def tick(self):
        direction = self.camera_angle.direction() * self.speed
        self.velocity.y -= .5
        self.pos += self.velocity

        if sw.inputting.Input.get_press(K_w):
            self.pos.x -= math.sin(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z -= math.cos(math.radians(self.camera_angle.x)) * self.speed
        if sw.inputting.Input.get_press(K_s):
            self.pos.x += math.sin(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z += math.cos(math.radians(self.camera_angle.x)) * self.speed
        if sw.inputting.Input.get_press(K_a):
            self.pos.x -= math.cos(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z += math.sin(math.radians(self.camera_angle.x)) * self.speed
        if sw.inputting.Input.get_press(K_d):
            self.pos.x += math.cos(math.radians(self.camera_angle.x)) * self.speed
            self.pos.z -= math.sin(math.radians(self.camera_angle.x)) * self.speed
        self.pos.y = max(self.pos.y, 20)
        if sw.inputting.Input.get_pressed(K_SPACE) and self.pos.y <= 20:
            self.velocity.y = 20

        if sw.inputting.Input.get_press(K_TAB):
            self.perspective = not self.perspective

        if sw.inputting.Input.get_press(K_q):
            self.fov += 1

        if sw.inputting.Input.get_press(K_e):
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
        self.camera_angle.y = min(89.9, max(-89.9, self.camera_angle.y))

        # self.camera_angle = Vec3(0, 0, 0)
        main_cam.angles = self.camera_angle

        if self.mouse_x == 0 or self.mouse_x == screen_size[0] - 1:
            pygame.mouse.set_pos(screen_size[0] // 2, self.mouse_y)
            self.mouse_x = screen_size[0] // 2
        if self.mouse_y == 0 or self.mouse_y == screen_size[1] - 1:
            pygame.mouse.set_pos(self.mouse_x, screen_size[1] // 2)
            self.mouse_y = screen_size[1] // 2

    def draw(self):
        for i in range(20):
            for j in range(20):
                for k in range(-10, 3):
                    draw_block((i, k, j), ("grass_block_top.png", "grass_block_side.png", "grass_block_side.png", "grass_block_side.png", "grass_block_side.png", "dirt.png"))

block_state = {}
def draw_block(coordinates, textures):

    block_state[coordinates] = 1
    size = 10
    coordinates_use = Vec3(*coordinates) * size
    angle = [
        Vec3(90, 0, 0),
        Vec3(0, 90, 0),
        Vec3(0, 180, 0),
        Vec3(0, 270, 0),
        Vec3(0, 0, 0),
        Vec3(90, 0, 0),
    ]
    position = [
        Vec3(0, size / 2, 0),
        Vec3(size / 2, 0, 0),
        Vec3(0, 0, size / 2),
        Vec3(-size / 2, 0, 0),
        Vec3(0, 0, -size / 2),
        Vec3(0, -size / 2, 0),
    ]
    face_offset = [
        Vec3(0,1,0),
        Vec3(1,0,0),
        Vec3(0,0,1),
        Vec3(-1,0,0),
        Vec3(0,0,-1),
        Vec3(0,-1,0),
    ]

    for i, texture in enumerate(textures):
        point = Vec3(*coordinates) + face_offset[i]
        if block_state.get((point.x, point.y, point.z)) == None:
            image = sw.graphics.texture.Texture.get_texture(texture.split(".")[0])
            if image == None:
                image = sw.graphics.texture.Texture.set_texture(texture.split(".")[0], Path.cwd() / "resources" / "block" / texture)

            sw.entity.Draw.draw_image(image, coordinates_use + position[i], Vec3(size, size, 1), angle[i], (122, 189, 106, 255) if texture == "grass_block_top.png" else (255,255, 255, 255))
    


test()

sw.run()