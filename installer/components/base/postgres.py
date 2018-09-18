
from ..syspkg import SysPkgComponent

class Postgres(SysPkgComponent):
    def __init__(self, config):
        self.name = "postgres"
        SysPkgComponent.__init__(self, config, self.name)
