import logging
import coloredlogs
from logging.handlers import RotatingFileHandler
import os
import errno

def create_logging_directory():
    logs_dir = os.path.join(os.path.dirname(__file__), os.pardir, 'logs')

    try:
        os.makedirs(logs_dir)
    except OSError, error:
        if error.errno == errno.EEXIST:
            pass

    return logs_dir


def main():

    logs_dir = create_logging_directory()

    error_log_path = os.path.join(logs_dir, "esgf_error_log.out")
    info_log_path = os.path.join(logs_dir, "esgf_info_log.out")
    #----------------------------------------------------------------------
    logger = logging.getLogger('esgf_logger')
    logger.setLevel(logging.DEBUG)

    print logger.handlers

    # create file handler which logs even debug messages
    # add a rotating handler
    error_handler = RotatingFileHandler(error_log_path, maxBytes=10*1024*1024,
                                  backupCount=5)

    info_handler = RotatingFileHandler(info_log_path, maxBytes=10*1024*1024,
                                  backupCount=5)
    # fh = logging.FileHandler(PATH)
    error_handler.setLevel(logging.ERROR)
    info_handler.setLevel(logging.INFO)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter("%(levelname)s - %(filename)s - %(lineno)s - %(funcName)s - %(asctime)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')

    error_handler.setFormatter(formatter)
    info_handler.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(error_handler)
    logger.addHandler(info_handler)
    logger.addHandler(ch)

    #added coloredlogs
    colored_log_file = open(os.path.join(logs_dir, "esgf_colored_log.out"), "w")
    coloredlogs.install(level='DEBUG', logger=logger, stream=colored_log_file)

if __name__ == '__main__':
    main()
