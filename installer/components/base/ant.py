from ..syspkg import SysPkgComponent

class Ant(SysPkgComponent):
    def __init__(self, config):
        self.name = "ant"
        SysPkgComponent.__init__(self, config, self.name)
