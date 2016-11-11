''' Utility class for porting Bash Shell code to Python '''

import sys
import os
import subprocess
import signal


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
