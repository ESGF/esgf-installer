from .installer import Installer
from base.esg_java import Java, Ant

class Director(object):
    ''' A class for managing the flow of the program '''
    def __init__(self):
        self.params = None
        # Store what components are needed for each node type.
        self.node_types = {
            "base": { Java, Ant }
        }
    def pre_check(self):
        # Check privileges, OS, PATH, etc..
        print "Checking prerequisites..."

    def get_cmd_line(self):
        # A sample input from cmd line
        self.params = {
            "install" : True,
            "types": "base"
        }
    def begin(self):
        print "Starting Director"
        if self.params["install"]:
            # Find unique components, as there may be overlap
            component_types = set()
            for node_type in self.params["types"].split():
                component_types &= self.node_types[node_type]
            installer = Installer(component_types)
            # installer.status_check()
            print installer.status_check()
            installer.install()
            print installer.status_check()
