'''
A module for the managment of an env file with exports and sources.
Note to only use the instantiated version at the bottom to maintain state
throughout the program.
'''

class _EnvWriter(object):
    ''' A class for managing the ESG environment file '''
    def __init__(self, envfile):
        self.envfile = envfile
        open(self.envfile, "a").close()

    def add_source(self, source_env):
        ''' When envfile is sourced, source_env will also be sourced '''
        with open(self.envfile, "a") as envfile:
            envfile.write("source {}\n".format(source_env))

    def export(self, variable, value):
        ''' Writes the export statement to be executed when envfile is sourced '''
        with open(self.envfile, "a") as envfile:
            envfile.write("export {}={}\n".format(variable, value))

    def read(self):
        ''' Returns the contents of the envfile '''
        with open(self.envfile, "r") as envfile:
            return envfile.read()


EnvWriter = _EnvWriter("/etc/esg.env")
