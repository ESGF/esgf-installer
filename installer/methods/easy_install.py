import logging

from plumbum import TEE

from .package_manager import Pip
from .distribution import FileManager

class EasyInstall(Pip, FileManager):
    def __init__(self, components):
        Pip.__init__(self, components)
        FileManager.__init__(self, components)
        self.log = logging.getLogger(__name__)

    def _install(self, names):
        FileManager._install(self, names)
        for component in self.components:
            if component["name"] not in names:
                continue
            try:
                env = component["conda_env"]
            except KeyError:
                env = self.installer_env
            if self._get_env(env) is None:
                self._create_env_w_pip(env)
            args = [env, "easy_install", component["dest"]]
            result = self.run_in_env.__getitem__(args) & TEE

    def _uninstall(self):
        Pip._uninstall(self)

    def _versions(self):
        return Pip._versions(self)
