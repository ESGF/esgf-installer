import os.path as path

from plumbum import local
from plumbum import TEE

from .conda import Conda
from ..utils import pushd

class Command(Conda):
    ''' Install components using and arbibtrary command '''
    def __init__(self, components):
        Conda.__init__(self, components)
        self.executed = set()
        self.run_in_env = local.get(path.join(path.dirname(__file__), "run_in_env.sh"))

    def _install(self, names):
        for component in self.components:
            if component["name"] not in names:
                continue
            try:
                with pushd(component["working_dir"]):
                    self._execute(component)
            except KeyError:
                self._execute(component)

    def _execute(self, component):
        args = []
        try:
            env = component["conda_env"]
            args += [env, component["command"]]
        except KeyError:
            cmd = local.get(component["command"])
        else:
            if self._get_env(env) is None:
                self._create_env(env, ["python<3"], [])
            cmd = self.run_in_env
        try:
            args += component["args"]
        except KeyError:
            pass
        if args:
            result = cmd.__getitem__(args) & TEE
        else:
            result = cmd.run_tee()
        self.executed.add(component["name"])

    def _uninstall(self):
        pass

    def _versions(self):
        versions = {}
        for component in self.components:
            if component["name"] in self.executed:
                versions[component["name"]] = "1"
            else:
                versions[component["name"]] = None
        return versions
