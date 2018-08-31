'''
A module for the managment of an env file with exports and sources.
Note to only use the instantiated version at the bottom to maintain state
throughout the program.
'''
ENV = {
    "sources": [],
    "exports": {}
}
class _EnvWriter(object):
    ''' A class for managing the ESG environment file '''
    def __init__(self, envfile):
        self.envfile = envfile
        self.sources = ENV["sources"]
        self.exports = ENV["exports"]

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


EnvWriter = _EnvWriter("/etc/esg.env")
