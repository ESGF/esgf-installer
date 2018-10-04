import logging
import grp
import os
import pwd

from plumbum import local
from plumbum import TEE

from .generic import Generic

class UserMethod(Generic):
    ''' User creation '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.create_cmds = {
            "useradd":{
                "create_args": []
            }
        }
        self.del_cmds = {
            "userdel": {
                "delete_args": []
            }
        }
        self.create_user = local.get(*self.create_cmds.keys())
        self.create_cmd_name = os.path.basename(str(self.create_user))
        self.delete_user = local.get(*self.del_cmds.keys())
        self.delete_cmd_name = os.path.basename(str(self.delete_user))

    def _install(self, names):
        for component in self.components:
            if component.name not in names:
                continue
            try:
                args = component.options
            except AttributeError:
                args = []
            args += self.create_cmds[self.create_cmd_name]["create_args"]
            args += [component.username]
            result = self.create_user.__getitem__(args) & TEE

    def _uninstall(self):
        for component in self.components:
            args = self.del_cmds[self.delete_cmd_name]["delete_args"]
            args += [component.username]
            result = self.delete_user.__getitem__(args) & TEE

    def _versions(self):
        versions = {}
        for component in self.components:
            try:
                pwd.getpwnam(component.username)
            except KeyError:
                versions[component.name] = None
            else:
                versions[component.name] = "1"
        return versions


class GroupMethod(Generic):
    ''' Group creation '''
    def __init__(self, components):
        Generic.__init__(self, components)
        self.create_cmds = {
            "groupadd":{
                "create_args": []
            }
        }
        self.del_cmds = {
            "groupdel": {
                "delete_args": []
            }
        }
        self.create_group = local.get(*self.create_cmds.keys())
        self.create_cmd_name = os.path.basename(str(self.create_group))
        self.delete_group = local.get(*self.del_cmds.keys())
        self.delete_cmd_name = os.path.basename(str(self.delete_group))

    def _install(self, names):
        for component in self.components:
            if component.name not in names:
                continue
            try:
                args = component.options
            except AttributeError:
                args = []
            args += self.create_cmds[self.create_cmd_name]["create_args"]
            args += [component.groupname]
            result = self.create_group.__getitem__(args) & TEE

    def _uninstall(self):
        for component in self.components:
            args = self.del_cmds[self.delete_cmd_name]["delete_args"]
            args += [component.groupname]
            result = self.delete_group.__getitem__(args) & TEE

    def _versions(self):
        versions = {}
        for component in self.components:
            try:
                grp.getgrnam(component.groupname)
            except KeyError:
                versions[component.name] = None
            else:
                versions[component.name] = "1"
        return versions
