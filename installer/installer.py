
from base.esg_java import Java, Ant
from .install_codes import OK, NOT_INSTALLED, BAD_VERSION

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, node_types):
        # Store what components are needed for each node type.
        nodes = {
            # "data": [ Foo ],
            # "index": [ Foo, Bar ]
            "base": [ Java, Ant ]
        }
        self.components_status = {
            OK: [],
            NOT_INSTALLED: [],
            BAD_VERSION: []
        }
        # Find unique components, as there may be overlap
        component_types = set()
        for node_type in node_types:
            for component in nodes[node_type]:
                component_types.add(component)

        # Initialize the unique types and give them a dictionary to store information
        self.components = []
        for component in component_types:
            self.components.append(component())

    def status_check(self):
        # Check the status of of component
        for component in self.components:
            self.components_status[component.status()].append(component)

        divider = "_"*30
        if len(self.components_status[NOT_INSTALLED]) != 0:
            print "{}\nNot installed:".format(divider)
            for component in self.components_status[NOT_INSTALLED]:
                print "    {}".format(component.__name__)
        if len(self.components_status[BAD_VERSION]) != 0:
            print "{}\nInvalid Version:".format(divider)
            for component in self.components_status[BAD_VERSION]:
                print "    {}".format(component.__name__)
        if len(self.components_status[OK]) != 0:
            print "{}\nAlready Installed:".format(divider)
            for component in self.components_status[OK]:
                print "    {}".format(type(component).__name__)

    def install(self):
        # Handle components based on their status
        pass
