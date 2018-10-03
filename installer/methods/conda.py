from .generic import Generic

from plumbum import local
from plumbum import TEE

class Conda(Generic):
    ''' Install components using the pip command line tool '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.conda = local.get("conda")
        self.install_args = ["install", "-y"]
        self.uninstall_cmd = ["uninstall", "-y"]

    def _install(self, names):
        conda_list = []
        channels = []
        for component in self.components:
            if component.name not in names:
                continue
            try:
                channels += component.channels
            except AttributeError:
                pass
            try:
                conda_name = component.conda_name
            except AttributeError:
                conda_name = component.name
            conda_list.append(conda_name)
        if conda_list:
            if channels:
                args = self.install_args + conda_list + ["-c"] + channels
            else:
                args = self.install_args + conda_list
