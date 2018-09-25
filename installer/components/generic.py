from ..utils import populate
from ..utils import populated
from ..utils import check_populatable

class GenericComponent(object):
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.replacements = {"name": name}
        for param in self.config:
            if not isinstance(self.config[param], basestring):
                continue
            check_populatable(param, self.config[param], self.config.keys()+self.replacements.keys())
        all_populated = False
        while not all_populated:
            all_populated = True
            for param in self.config:
                if not isinstance(self.config[param], basestring):
                    continue
                if param in self.replacements:
                    continue
                if populated(self.config[param]):
                    self.replacements[param] = self.config[param]
                else:
                    self.config[param] = populate(self.config[param], self.replacements)
                    all_populated = False
