from ..syspkg import SysPkgComponent

class HTTPD(SysPkgComponent):
    def __init__(self, name, config):
        SysPkgComponent.__init__(self, name, config)
