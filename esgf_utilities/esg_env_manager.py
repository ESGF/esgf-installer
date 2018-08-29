class _EnvWriter(object):
    def __init__(self, envfile):
        self.env = {}
        self.envfile = envfile

    def add_source(self, source_env):
        with open(self.envfile, "w") as envfile:
            for key in self.env:
                envfile.write("export {}={}\n".format(key, self.env[key]))
            envfile.write("source {}".format(source_env))

    def write(self, variable, value):
        self.env[variable] = value
        with open(self.envfile, "w") as envfile:
            for key in self.env:
                envfile.write("export {}={}\n".format(key, self.env[key]))

    def read(self):
        with open(self.envfile, "r") as envfile:
            print envfile.read()

EnvWriter = _EnvWriter("sample.env")
