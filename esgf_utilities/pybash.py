''' Utility class for porting Bash Shell code to Python '''

import sys
import os
import errno
import re
import subprocess
from contextlib import contextmanager
import logging

logger = logging.getLogger("esgf_logger" +"."+ __name__)


class PyBashException(Exception):
    '''
      Custom exception class
    '''

    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return repr(self.value)


def mkdir_p(path, mode = 0777):
    '''Mimics Bash's mkdir -p executable; Creates the directory and any subdirectories listed in path.  If the path already exists, then return silently'''
    try:
        os.makedirs(path, mode)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            logger.debug("%s already exists.", path)
        else:
            raise

def getLongestSequenceSize(search_str, polymer_str):
    matches = re.findall(r'(?:\b%s\b\s?)+' % search_str, polymer_str)
    longest_match = max(matches)
    return longest_match.count(search_str)


def touch(path):
    '''
        Mimics Bash's touch command; Creates a new file and sets the access and modified times
    '''
    with open(path, 'a'):
        os.utime(path, None)

def trim_string_from_head(string_name, separator="/"):
    '''
        Mimics Bash's ##* Parameter Expansion; Splits a string by separator and returns the last token
        Example:
            (Bash)
            esg_installarg_file="/usr/local/bin/esg_installarg_file"
            echo ${esg_installarg_file##*/}

                output - > esg_installarg_file

            (Python)
            path = "/usr/local/bin/esg_installarg_file"
            print trim_string_from_tail(path)

                output -> esg_installarg_file
    '''
    return string_name.rsplit(separator,1)[-1]

def trim_string_from_tail(string_name, separator="/"):
    '''
        Mimics Bash's %%* Parameter Expansion; Splits a string by separator and returns the first token
        Example:
            (Bash)
            tomcat_version="8.0.33"
            echo ${tomcat_version%%.*}

                output -> 8

            (Python)
            tomcat_version="8.0.33"
            print  trim_string_from_tail(tomcat_version)

            output -> 8

    '''
    # string_regex = r"^\w+"
    # return re.search(string_regex, string_name).group()
    return string_name.split(separator,1)[0]

@contextmanager
def pushd(new_dir):
    '''
        Mimic's Bash's pushd executable; Adds new_dir to the directory stack
        Usage:
        with pushd(some_dir):
            print os.getcwd() # "some_dir"
            some_actions
        print os.getcwd() # "starting_directory"
    '''
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    yield
    os.chdir(previous_dir)


def symlink_force(target, link_name):
    '''Creates a symlink; if a symlink already exists, delete it and create new symlink'''
    logger.debug("Creating symlink from %s -> %s", target, link_name)
    try:
        os.symlink(target, link_name)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(link_name)
            os.symlink(target, link_name)
        else:
            raise e
