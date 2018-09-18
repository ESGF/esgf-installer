
from ..distribution import DistComponent

class Thredds(DistComponent):
    def __init__(self, config):
        self.name = "thredds"
        DistComponent.__init__(self, config, self.name)
