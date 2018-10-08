import logging

from .generic import GenericComponent

class CommandComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        self.command = config["command"]
        try:
            self.args = config["args"]
        except KeyError:
            pass
