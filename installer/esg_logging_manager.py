import logging
import coloredlogs
from logging.handlers import RotatingFileHandler

PATH = "esgf_log.out"
#----------------------------------------------------------------------
def create_rotating_log(name, path=PATH):
    """
    Creates a rotating log
    """
    logger = logging.getLogger(name)


    # add a rotating handler
    handler = RotatingFileHandler(path, maxBytes=10*1024*1024,
                                  backupCount=5)

    # create formatter
    formatter = logging.Formatter("%(levelname)s - %(filename)s - %(lineno)s - %(funcName)s - %(asctime)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')
    colored_log_file = open("esgf_colored_log.out", "w")
    coloredlogs.install(level='DEBUG', logger=logger, stream=colored_log_file)
    # add formatter to handler
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger
