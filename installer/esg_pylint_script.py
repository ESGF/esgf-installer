import glob
import os
import datetime
import time
import logging
from pylint.lint import Run
import pprint
import esg_bash2py
import getopt
import sys

logging.basicConfig(
    format="%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create folder pylint_score_reports
esg_bash2py.mkdir_p("pylint_score_reports")

# get all files that contain the esg*_**.py pattern
esgf_python_scripts = glob.glob("esg*_**.py")


# file_name = raw_input("Enter the script name to lint:")
# if file_name in esgf_python_scripts

def usage():
    print """Usage: -h | -i <filename> | -all"""

def main(argv):
    try:
        options, arguements = getopt.getopt(argv,"hi:all:")
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    for option, arguements in options:
        if option in ("-h", "--help"):
            usage()
            sys.exit(2)
        elif option == "-all":

            with open("pylint_score_reports/pylint_scores{date}.txt".format(date=time.strftime("%m_%d_%Y")), "a") as scores_file:
                scores_file.write("\n")
                scores_file.write(str(datetime.datetime.today())+"\n")
                for script in esgf_python_scripts:
                    print "script name:", script
                    scores_file.write("script name: {script}".format(script=script)+"\n")
                    results = Run([script], exit=False)
                    try:
                        scores_file.write("score: "+str(results.linter.stats["global_note"])+"\n")
                    except KeyError, error:
                        logger.error(error)
                        logger.error("Can't find score for %s", script)



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


