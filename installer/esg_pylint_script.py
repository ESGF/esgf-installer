import glob
import os
import datetime
import time
import logging
from pylint.lint import Run
import pprint
import esg_bash2py
import sys

logging.basicConfig(
    format="%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# create folder pylint_score_reports
esg_bash2py.mkdir_p("pylint_score_reports")

# get all files that contain the esg*_**.py pattern
esgf_python_scripts = glob.glob("esg*_**.py")


def usage():
    ''' Print proper usage message.'''
    print """Usage: esg_python_script [-h|-i <filename>|-all]"""


def scan_all():
    ''' Scan all python modules and append score to a file.'''
    with open("pylint_score_reports/pylint_scores{date}.txt".format(date=time.strftime("%m_%d_%Y")), "a") as scores_file:
        scores_file.write("\n")
        scores_file.write(str(datetime.datetime.today()) + "\n")
        for script in esgf_python_scripts:
            print "script name:", script
            scores_file.write(
                "script name: {script}".format(script=script) + "\n")
            results = Run([script], exit=False)
            try:
                scores_file.write(
                    "score: " + str(results.linter.stats["global_note"]) + "\n")
            except KeyError, error:
                logger.error(error)
                logger.error("Can't find score for %s", script)


def scan_one(filename):
    ''' Scan specified python modules and append score to a file with module name.'''
    with open("pylint_score_reports/pylint_scores_" + filename + "{date}.txt".format(date=time.strftime("%m_%d_%Y")), "a") as scores_file:
        scores_file.write("\n")
        scores_file.write(str(datetime.datetime.today()) + "\n")
        if filename in esgf_python_scripts:
            print "script name:", filename
            scores_file.write("Evaluating: {}".format(filename) + "\n")
            results = Run([filename], exit=False)
            try:
                scores_file.write(
                    "score: " + str(results.linter.stats["global_note"]) + "\n")
            except KeyError, error:
                logger.error(error)
                logger.error("Can't find score for %s", script)


def main(argv):
    ''' Handle main program logic.'''
    if len(argv) < 2:
        usage()
        sys.exit(1)

    if argv[1] in ("-h", "--help"):
        usage()
        sys.exit(1)
    elif argv[1] in ('-a', '--all'):
        print "Scanning all files..."
        scan_all()
    elif argv[1] == "-i":
        if argv[2] == None:
            print "No file detected!"

            sys.exit(1)
        filename = argv[2]
        scan_one(filename)
    else:
        print "Cannot recognize '{}'".format(argv[1])
        usage()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
