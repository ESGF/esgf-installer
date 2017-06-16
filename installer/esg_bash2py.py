''' Utility class for porting Bash Shell code to Python '''

import sys
import os
import errno
import re
import subprocess
from contextlib import contextmanager


class Bash2PyException(Exception):
    '''
      Custom exception class
    '''

    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Bash2Py(object):
    '''
      Wrapper class for holding the values returned from Bash commands
    '''
    __slots__ = ["val"]

    def __init__(self, value=''):
        self.val = value

    def setValue(self, value=None):
        self.val = value
        return value

    def postinc(self, inc=1):
        tmp = self.val
        self.val += inc
        return tmp

def mkdir_p(path, mode = 0777):
    try:
        os.makedirs(path, mode)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def getLongestSequenceSize(search_str, polymer_str):
    matches = re.findall(r'(?:\b%s\b\s?)+' % search_str, polymer_str)
    longest_match = max(matches)
    return longest_match.count(search_str)

def GetVariable(name, local=locals()):
    '''
      Looks for variables defined in the local and then module namespaces; returns None if not found
    '''
    if name in local:
        return local[name]
    if name in globals():
        return globals()[name]
    return None


def Make(name, local=locals()):
    '''
      Check to see if a local variable exists; if not create a global variable with a value of 0
    '''
    ret = GetVariable(name, local)
    if ret is None:
        ret = Bash2Py(0)
        globals()[name] = ret
    return ret


def GetValue(name, local=locals()):
    '''
      get the value of a given variable; return an empty string if the variable doesn't exist or has no value
    '''
    variable = GetVariable(name, local)
    if variable is None or variable.val is None:
        return ''
    return variable.val


def Array(value):
    '''
      if value is a List object, return the List; if value is plain String or Unicode String, convert to List;
      otherwise convert the value to a List 
    '''
    if isinstance(value, list):
        return value
    if isinstance(value, basestring):
        return value.strip().split(' ')
    return [value]


class Expand(object):
  '''
    A port of Bash's parameter expansion and substitution functionality
  '''

  @staticmethod
  def at():
      '''
        Port of Bash's positional parameter (@) operator
      '''
      if (len(sys.argv) < 2):
          return []
      return sys.argv[1:]

  @staticmethod
  def star(in_quotes):
      '''
        Port of Bash's positional parameter (*) operator
      '''
      if (in_quotes):
          if (len(sys.argv) < 2):
              return ""
          return " ".join(sys.argv[1:])
      return Expand.at()

  @staticmethod
  def exclamation():
      raise Bash2PyException("$! unsupported")

  @staticmethod
  def underbar():
      raise Bash2PyException("$_ unsupported")

  @staticmethod
  def colonMinus(name, value=''):
      '''
        Port of Bash's parameter substitution operator
        If parameter is null or unset, the alternate word is substituted, otherwise the return the parameter.
      '''
      try:
        name
      except NameError:
        print "variable undefined"
        return value
      else:
        ret = GetValue(name)
        if (ret is None or ret == ''):
            ret = value
        return ret

  @staticmethod
  def colonPlus(name, value=''):
      '''
        Port of Bash's parameter substitution operator
        ${parameter:+word}
        If parameter is null or unset, nothing is substituted, otherwise the expansion of word is substituted.
      '''
      ret = GetValue(name)
      if (ret is None or ret == ''):
          return ''
      return value

def touch(path):
    ''' 
        Mimics Bash's touch command
    '''
    with open(path, 'a'):
        os.utime(path, None)

def trim_string_from_head(string_name):
    '''
        Mimics Bash's ##* Parameter Expansion
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
    #TODO: Might refactor to use this: config.config_dictionary["tomcat_dist_url"].rsplit("/",1)[-1]
    # string_regex = r"\w*-*\w+$" 
    # return re.search(string_regex, string_name).group()
    return string_name.rsplit("/",1)[-1]

def trim_string_from_tail(string_name):
    '''
        Mimics Bash's %%* Parameter Expansion
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
    string_regex = r"^\w+"
    return re.search(string_regex, string_name).group()

@contextmanager
def pushd(new_dir):
    '''
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
    try:
        os.symlink(target, link_name)
    except OSError, e:
        if e.errno == errno.EEXIST:
            os.remove(link_name)
            os.symlink(target, link_name)
        else:
            raise e

def source(script, update=1):
  ''' Mimics Bash's source function '''
  pipe = subprocess.Popen(". %s; env" % script, stdout=subprocess.PIPE, shell=True)
  data = pipe.communicate()[0]

  env = dict((line.split("=", 1) for line in data.splitlines()))
  if update:
      os.environ.update(env)

  return env