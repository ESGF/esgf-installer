import logging

from .generic import GenericComponent

class UserComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        self.username = config["username"]
        try:
            self.options = config["options"]
        except KeyError:
            pass

class GroupComponent(GenericComponent):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        GenericComponent.__init__(self, name, config)
        self.groupname = config["groupname"]
        try:
            self.options = config["options"]
        except KeyError:
            pass
