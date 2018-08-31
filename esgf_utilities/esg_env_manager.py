'''
A module for the managment of an env file with exports and sources.
Note to only use the instantiated version at the bottom to maintain state
throughout the program.
'''
import shelve

class _EnvWriter(object):
    ''' A class for managing the ESG environment file '''
    def __init__(self, envfile, shelf_file):
        self.envfile = envfile
        self.env = shelve.open(shelf_file)
        source_key = "sources"
        export_key = "exports"
        if source_key not in self.env:
            self.env[source_key] = []
        if export_key  not in self.env:
            self.env[export_key ] = {}
        self.sources = self.env[source_key]
        self.exports = self.env[export_key]

    def add_source(self, source_env):
        ''' When envfile is sourced, source_env will also be sourced '''
        self.sources += [source_env]
        self._rewrite()

    def export(self, variable, value):
        ''' Writes the export statement to be executed when envfile is sourced '''
        self.exports[variable] = value
        self._rewrite()

    def _rewrite(self):
        with open(self.envfile, "w") as envfile:
            for export in self.exports:
                envfile.write("export {}={}\n".format(export, self.exports[export]))
            for source in self.sources:
                envfile.write("source {}\n".format(source))

    def read(self):
        ''' Returns the contents of the envfile '''
        with open(self.envfile, "r") as envfile:
            return envfile.read()


EnvWriter = _EnvWriter("sample.env", "/tmp/esg.env")
