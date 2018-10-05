'''
A module for the managment of an env file with exports and sources.
'''
import json

class _EnvWriter(object):
    ''' A class for managing the ESG environment file '''
    def __init__(self, envfile):
        self.envfile = envfile
        self.env_json = envfile + ".json"
        try:
            with open(self.env_json, "r") as env_json_file:
                existing_env = json.load(env_json_file)
            self.sources = existing_env["sources"]
            self.exports = existing_env["exports"]
        except IOError:
            # File does not exist, init empty sources and exports
            self.sources = []
            self.exports = {}

    def add_source(self, source_env):
        ''' When envfile is sourced, source_env will also be sourced '''
        if source_env not in self.sources:
            self.sources.append(source_env)
        self._rewrite()

    def export(self, variable, value):
        ''' Writes the export statement to be executed when envfile is sourced '''
        self.exports[variable] = value
        self._rewrite()

    def append_to_path(self, path_var, value):
        ''' Appends a path to a colon seperated path variable '''
        try:
            path_elements = self.exports[path_var].split(":")
        except KeyError:
            self.export(path_var, value)
        else:
            path_elements.append(value)
            new_value = ":".join(path_elements)
            self.export(path_var, new_value)

    def prepend_to_path(self, path_var, value):
        ''' Prepends a path to a colon seperated path variable '''
        try:
            path_elements = self.exports[path_var].split(":")
        except KeyError:
            self.export(path_var, value)
        else:
            path_elements.prepend(value)
            new_value = ":".join(path_elements)
            self.export(path_var, new_value)

    def _rewrite(self):
        with open(self.envfile, "w") as envfile:
            for export in self.exports:
                envfile.write("export {}={}\n".format(export, self.exports[export]))
            for source in self.sources:
                envfile.write("source {}\n".format(source))

        with open(self.env_json, "w") as env_json_file:
            env = {
                "sources": self.sources,
                "exports": self.exports
            }
            json.dump(env, env_json_file)

    def read(self):
        ''' Returns the contents of the envfile '''
        with open(self.envfile, "r") as envfile:
            return envfile.read()


EnvWriter = _EnvWriter("/etc/esg.env")
