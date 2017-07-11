import logging
from logging.handlers import RotatingFileHandler

PATH = "esgf_log.out"
#----------------------------------------------------------------------
def create_rotating_log(name, path=PATH):
    """
    Creates a rotating log
    """
    logging.basicConfig(format = "%(levelname): %(lineno)s %(funcName)s: %(asctime)s", level=logging.DEBUG, datefmt='%m/%d/%Y %I:%M:%S %p')
    logger = logging.getLogger(name)

    # add a rotating handler
    handler = RotatingFileHandler(path, maxBytes=8000,
                                  backupCount=5)
    logger.addHandler(handler)
    return logger
