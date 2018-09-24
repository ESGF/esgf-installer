import logging

from .installer import Installer
from .components.components import ALL

class Director(object):
    ''' A class for managing the flow of the program '''
    def __init__(self, args):
        self.log = logging.getLogger(__name__)
        self.args = args

    def pre_check(self):
        # Check privileges, OS, PATH, etc..
        print "Checking prerequisites"

    def begin(self):
        print "Starting Director"
        if self.args.install is not None:
            # Find required methods and components
            requirements = {}
            if self.args.type:
                node_types = self.args.type
            else:
                node_types = ALL.keys()
            for node_type in node_types:
                for method_type in ALL[node_type]:
                    if method_type not in requirements:
                        requirements[method_type] = ALL[node_type][method_type]
                    else:
                        requirements[method_type].update(ALL[node_type][method_type])

            installer = Installer(requirements, self.args.install)
            installer.install()

        elif self.args.uninstall is not None:
            requirements = {}
            if self.args.type:
                node_types = self.args.type
            else:
                node_types = ALL.keys()
            for node_type in node_types:
                for method_type in ALL[node_type]:
                    if method_type not in requirements:
                        requirements[method_type] = ALL[node_type][method_type]
                    else:
                        requirements[method_type].update(ALL[node_type][method_type])

            installer = Installer(requirements, self.args.uninstall)
            installer.uninstall()
