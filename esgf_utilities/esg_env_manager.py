'''
A module for the managment of an env file with exports and sources.
Note to only use the instantiated version at the bottom to maintain state
throughout the program.
'''

class _EnvWriter(object):
    ''' A class for managing the ESG environment file '''
    def __init__(self, envfile):
        self.env = {}
        self.envfile = envfile

    def add_source(self, source_env):
        ''' When envfile is sourced, source_env will also be sourced '''
        with open(self.envfile, "w") as envfile:
            for key in self.env:
                envfile.write("export {}={}\n".format(key, self.env[key]))
            envfile.write("source {}".format(source_env))

    def write(self, variable, value):
        ''' Writes the export statement to be executed when envfile is sourced '''
        self.env[variable] = value
        with open(self.envfile, "w") as envfile:
            for key in self.env:
                envfile.write("export {}={}\n".format(key, self.env[key]))

    def read(self):
        ''' Returns the contents of the envfile '''
        with open(self.envfile, "r") as envfile:
            return envfile.read()


EnvWriter = _EnvWriter("/etc/esg.env")
