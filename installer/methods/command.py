import logging
import os.path as path

from plumbum import local
from plumbum import TEE
from plumbum.commands import ProcessExecutionError

from .conda import Conda
from ..utils import pushd

class Command(Conda):
    ''' Install components using and arbibtrary command '''
    def __init__(self, components):
        Conda.__init__(self, components)
        self.log = logging.getLogger(__name__)
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
        okay, warn, crit = self._returncodes(component)
        try:
            if args:
                result = cmd.__getitem__(args) & TEE
            else:
                result = cmd.run_tee()
        except ProcessExecutionError as err:
            rc = err.retcode
            print rc
            if rc in okay:
                self.log.info("Okay code %s encountered for %s", rc, component["name"])
                self.log.info(str(err))
            elif warn is not None and rc in warn:
                self.log.warning("Warning code %s encountered for %s", rc, component["name"])
                self.log.warning(str(err))
            else:
                raise

        if crit is not None and rc in crit:
            self.log.error("Critical code %s encountered for %s", rc, component["name"])
            raise ProcessExecutionError

        self.executed.add(component["name"])

    def _returncodes(self, component):
        try:
            okay = component["okay_rc"]
        except KeyError:
            okay = [0]
        try:
            warn = component["warn_rc"]
        except KeyError:
            warn = None
        try:
            crit = component["crit_rc"]
        except KeyError:
            crit = None
        return okay, warn, crit

    def _uninstall(self):
        pass

    def _versions(self):
        versions = {}
        for component in self.components:
            try:
                check_args = component["check_args"]
            except KeyError:
                check_args = None
            try:
                check_fn = component["check_fn"]
            except KeyError:
                if component["name"] in self.executed:
                    versions[component["name"]] = "1"
                else:
                    versions[component["name"]] = None
            else:
                if check_args:
                    bool_res = bool(check_fn(*check_args))
                else:
                    bool_res = check_fn()
                if bool_res:
                    versions[component["name"]] = "1"
                else:
                    versions[component["name"]] = None
        return versions
