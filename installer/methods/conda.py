
from plumbum import local
from plumbum import TEE

from .package_manager import Pip

class Conda(Pip):
    ''' Install components using the pip command line tool '''
    def __init__(self, components):
        Pip.__init__(self, components)
        self.conda = local.get("conda")
        self.install_args = ["install", "-y"]
        self.uninstall_args = ["uninstall", "-y"]

    def _install(self, names):
        conda_list = []
        channels = set()
        for component in self.components:
            if component.name not in names:
                continue
            try:
                for channel in component.channels:
                    channels.add(channel)
            except AttributeError:
                pass
            try:
                conda_name = component.conda_name
            except AttributeError:
                conda_name = component.name
            conda_list.append(conda_name)
        if conda_list:
            if channels:
                channel_args = []
                for channel in channels:
                    channel_args += ["-c", channel]
                args = self.install_args + conda_list + channel_args
            else:
                args = self.install_args + conda_list
            result = self.conda.__getitem__(args) & TEE

    def _uninstall(self):
        conda_list = [component.name for component in self.components]
        if conda_list:
            args = self.uninstall_args + conda_list
            result = self.conda.__getitem__(args) & TEE
