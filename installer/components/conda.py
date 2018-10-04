import logging

from .generic import GenericComponent

class CondaComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        try:
            self.conda_name = self.config["conda_name"]
        except KeyError:
            pass
        try:
            self.channels = self.config["channels"]
        except KeyError:
            pass
