
from base.esg_java import Java, Ant

# Codes to be used by Installer to figure out what to do
OK = 0
NOT_INSTALLED = 1
BAD_VERSION = 2

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, node_types):
        # Store what components are needed for each node type.
        nodes = {
            # "data": [ Foo ],
            # "index": [ Foo, Bar ]
            "base": [ Java, Ant ]
        }
        # Find unique components, as there may be overlap
        component_types = set()
        for node_type in node_types:
            for component in nodes[node_type]:
                component_types.add(component)

        # Initialize the unique types and give them a dictionary to store information
        self.components = {}
        for component in component_types:
            self.components[component()] = {"status": None}
        print "Initialized Components:", self.components

    def status_check(self):
        # Check the status of of component
        for component in self.components:
            self.components[component]["status"] = component.status()

    def install(self):
        # Handle components based on their status
        for component in self.components:
            if self.components[component]["status"] != OK:
                component.install()

if __name__ == "__main__":
    installer = Installer(["base"])
    installer.status_check()
    installer.install()
