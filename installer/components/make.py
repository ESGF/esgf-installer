import logging

from .files import FileComponent

class MakeComponent(FileComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        FileComponent.__init__(self, name, config)
        try:
            self.make_dir = self.config["make_dir"]
        except KeyError:
            self.make_dir = self.config["dest"]
