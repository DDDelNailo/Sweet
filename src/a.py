import sweet as sw

sw.init()
class test(sw.Entity):
    def __init__(self):
        super().__init__((0, 0), order=3, tick=True)



test()

sw.run()