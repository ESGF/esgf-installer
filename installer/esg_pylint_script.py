#!/usr/local/bin/python2.7

import glob
import os
import datetime
import time
import logging
from pylint.lint import Run
import pprint
import esg_bash2py

logging.basicConfig(
    format="%(levelname): %(lineno)s %(funcName)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

esg_bash2py.mkdir_p("pylint_score_reports")

esgf_python_scripts = glob.glob("esg*_**.py")
print "esgf_python_scripts:", esgf_python_scripts
print "size of esgf_python_scripts: ", len(esgf_python_scripts)

# file_name = raw_input("Enter the script name to lint:")
# if file_name in esgf_python_scripts

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
