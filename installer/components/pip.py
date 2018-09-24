import logging

from ..utils import populate
from ..utils import populated
from ..utils import check_populatable

class PipComponent(object):
    def __init__(self, name, config):
        self.log = logging.getLogger(__name__)
        self.name = name
        replacements = {"name": name}
        for param in config:
            if not isinstance(config[param], basestring):
                continue
            check_populatable(param, config[param], config.keys()+replacements.keys())
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
        try:
            self.pip_name = config["pip_name"]
        except KeyError:
            pass
