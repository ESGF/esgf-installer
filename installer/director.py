from .installer import Installer
from .components.components import ALL

class Director(object):
    ''' A class for managing the flow of the program '''
    def __init__(self):
        self.params = None

    def pre_check(self):
        # Check privileges, OS, PATH, etc..
        print "Checking prerequisites..."

    def get_cmd_line(self):
        # A sample input from cmd line
        self.params = {
            "install" : True,
            "types": "base data"
        }
    def begin(self):
        print "Starting Director"
        if self.params["install"]:
            # Find unique components, as there may be overlap
            requirements = {}
            for node_type in self.params["types"].split():
                for method_type in ALL[node_type]:
                    if method_type not in requirements:
                        requirements[method_type] = ALL[node_type][method_type]
                    else:
                        requirements[method_type].update(ALL[node_type][method_type])
            print requirements
            installer = Installer(requirements)
            installer.install()
