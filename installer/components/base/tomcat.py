
from ..distribution import DistComponent

class Tomcat(DistComponent):
    def __init__(self, config):
        self.name = "tomcat"
        DistComponent.__init__(self, config, self.name)
