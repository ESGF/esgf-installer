
import logging

from .generic import GenericComponent

class FileComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        self.source = self.config["source"]
        self.dest = self.config["dest"]
        try:
            self.extract = self.config["extract"]
        except KeyError:
            pass
        try:
            self.tar_root_dir = self.config["tar_root_dir"]
        except KeyError:
            pass
        try:
            self.tag = self.config["tag"]
        except KeyError:
            pass
        try:
            owner = self.config["owner"]
        except KeyError:
            pass
        else:
            if isinstance(owner, basestring):
                self.owner_user = owner
            elif isinstance(owner, dict):
                self.owner_user = owner["user"]
                self.owner_group = owner["group"]
