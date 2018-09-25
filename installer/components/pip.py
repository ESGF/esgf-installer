import logging

from .generic import GenericComponent

class PipComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        try:
            self.pip_name = self.config["pip_name"]
        except KeyError:
            pass
