import logging
from logging.handlers import RotatingFileHandler

PATH = "esgf_log.out"
#----------------------------------------------------------------------
def create_rotating_log(name, path=PATH):
    """
    Creates a rotating log
    """
    esgf_logger = logging.getLogger(name)

    # add a rotating handler
    handler = RotatingFileHandler(path, maxBytes=10000,
                                  backupCount=5

    # handler.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to handler
    handler.setFormatter(formatter)

    esgf_logger.addHandler(handler)
    return esgf_logger
