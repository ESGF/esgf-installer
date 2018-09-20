
from ..utils import populate
from ..utils import populated

class PipComponent(object):
    def __init__(self, name, config):
        self.name = name
        replacements = {"name": name}
        all_populated = False
        while not all_populated:
            all_populated = True
            for param in config:
                if not isinstance(config[param], basestring):
                    continue
                if param in replacements:
                    continue
                if populated(config[param]):
                    replacements[param] = config[param]
                else:
                    config[param] = populate(config[param], replacements)
                    all_populated = False
        print replacements
        print config
