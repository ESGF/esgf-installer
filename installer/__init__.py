import logging
import sys
# import coloredlogs
from logging.handlers import RotatingFileHandler


print "Initializing loggers"
logging.basicConfig(format="%(levelname)s - %(filename)s - %(lineno)s - %(funcName)s - %(asctime)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG, stream=sys.stdout)
