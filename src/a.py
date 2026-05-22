import sweet as sw

sw.Display.set_resizable(True)
screen_size = sw.Display.screen_size
sw.Display.set_size((screen_size[0] - 100, screen_size[1] - 100))
sw.init()


class test(sw.Entity):
    def __init__(self):
        super().__init__((0, 0), None, (1, 1), 0, 0, 5, False, True, False)

    def draw(self):
        sw.__entity.Draw.draw_image()

test()

sw.run()