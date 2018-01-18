import logging
# import coloredlogs
from logging.handlers import RotatingFileHandler

PATH = "esgf_log.out"
#----------------------------------------------------------------------
logger = logging.getLogger('esgf_logger')
logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler(PATH)
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter("%(levelname)s - %(filename)s - %(lineno)s - %(funcName)s - %(asctime)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')

fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


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
    # colored_log_file = open("esgf_colored_log.out", "w")
    # coloredlogs.install(level='DEBUG', logger=logger, stream=colored_log_file)
    # add formatter to handler
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)
    consoleHandler.setFormatter(formatter)

    logger.addHandler(consoleHandler)

    logger.addHandler(handler)
    return logger
