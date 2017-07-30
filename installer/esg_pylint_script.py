#!/usr/local/bin/python2.7

import glob
import sys
import os
import datetime
import time
from pylint.lint import Run
from contextlib import contextmanager
import esg_bash2py
import esg_logging_manager

logger = esg_logging_manager.create_rotating_log(__name__)

# create folder pylint_score_reports
esg_bash2py.mkdir_p("pylint_score_reports")

# get all files that contain the esg*_**.py pattern
esgf_python_scripts = glob.glob("esg*_**.py")

#TODO: Might do this set difference operation to remove this script (esg_pylint_script) from the linting
# esgf_python_scripts = set(esgf_python_scripts) - set(glob("esg_pylint_script"))

@contextmanager
def suppress_stdout():
    '''Source: http://thesmithfam.org/blog/2012/10/25/temporarily-suppress-console-output-in-python/'''
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def usage():
    ''' Print proper usage message.'''
    print """Usage: esg_python_script [-h|-i <filename>|-all]"""


def scan_all():
    ''' Scan all python modules and append score to a file.'''
    with open("pylint_score_reports/pylint_scores{date}.txt".format(date=time.strftime("%m_%d_%Y")), "a") as scores_file:
        scores_file.write("\n")
        scores_file.write(str(datetime.datetime.today()) + "\n")
        for script_name in esgf_python_scripts:
            print "script name:", script_name
            scores_file.write(
                "script name: {script}".format(script=script_name) + "\n")
            with suppress_stdout():
                results = Run([script_name], exit=False)
            try:
                scores_file.write(
                    "score: " + str(results.linter.stats["global_note"]) + "\n")
            except KeyError, error:
                logger.error(error)
                logger.error("Can't find score for %s", script_name)


def scan_one(script_name):
    ''' Scan specified python modules and append score to a file with module name.'''
    with open("pylint_score_reports/pylint_scores_" + script_name + "{date}.txt".format(date=time.strftime("%m_%d_%Y")), "a") as scores_file:
        scores_file.write("\n")
        scores_file.write(str(datetime.datetime.today()) + "\n")
        if script_name in esgf_python_scripts:
            print "script name:", script_name
            scores_file.write("Evaluating: {}".format(script_name) + "\n")
            with suppress_stdout():
                results = Run([script_name], exit=False)
            try:
                scores_file.write(
                    "score: " + str(results.linter.stats["global_note"]) + "\n")
            except KeyError, error:
                logger.error(error)
                logger.error("Can't find score for %s", script_name)


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
