import logging
from logging.handlers import RotatingFileHandler

PATH = "esgf_log.out"
#----------------------------------------------------------------------
def create_rotating_log(name, path=PATH):
    """
    Creates a rotating log
    """
    logger = logging.getLogger(name)

    # add a rotating handler
    handler = RotatingFileHandler(path, maxBytes=10000,
                                  backupCount=5)

    # create formatter
    formatter = logging.Formatter("%(levelname):%(lineno)s %(funcName)s: %(asctime)s", datefmt='%m/%d/%Y %I:%M:%S %p')

    # add formatter to handler
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger
