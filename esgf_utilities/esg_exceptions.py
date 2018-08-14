class UnprivilegedUserError(Exception):
    pass

class WrongOSError(Exception):
    pass

class UnverifiedScriptError(Exception):
    pass

class NoNodeTypeError(Exception):
    pass

class InvalidNodeTypeError(Exception):
    pass

class SubprocessError(Exception):
    def __init__(self, data):
        self.data = data
    def __str__(self):
        return dict(self.data)
    def __repr__(self):
        return dict(self.data)
