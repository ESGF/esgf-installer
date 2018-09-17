from .sample_components import Java, Thredds, Tomcat
# from .methods.package_manager import PackageManager
from .methods.distribution import DistributionArchive

class Installer(object):
    # A class for handling the installation, updating and general management of components
    def __init__(self, component_types, component_config):
        method_types = {
            DistributionArchive: {Java, Thredds, Tomcat}
        }
        self.methods = set()
        for method_type in method_types:
            components = method_types[method_type] & component_types
            self.methods.add(method_type(components, component_config))

        self.divider = "_"*30
        self.header = self.divider + "\n{}"

    def status_check(self):
        # Check the status of each component
        print self.header.format("Checking status")
        statuses = {}
        for method in self.methods:
            statuses.update(method.statuses())
        return statuses

    def install(self):
        print self.header.format("Installing")
        for method in self.methods:
            method.install()

    def versions_installed(self):
        print self.header.format("Checking versions")
        versions = {}
        for method in self.methods:
            versions.update(method.versions())
        return versions
