'''
    Component Version Management Utility Functions
'''
import os
import subprocess
import re
import logging
from esg_init import EsgInit
import esg_bash2py
import esg_logging_manager

logger = esg_logging_manager.create_rotating_log(__name__)
config = EsgInit()

def version_comp(input_version1, input_version2):
    '''
            Takes two strings, splits them into epoch (before the last ':'),
            version (between the last ':' and the first '-'), and release
            (after the first '-'), and then calls _version_segment_cmp on
            each part until a difference is found.

            Empty segments are replaced with "-1" so that an empty segment
            can precede a non-empty segment when being passed to
            _version_segment_cmp.  As with _version_segment_cmp, leading
            zeroes will likely confuse comparison as this is still
            fundamentally a string sort to allow strings like "3.0alpha1".

            If $1 > $2, prints 1.  If $1 < $2, prints -1.  If $1 = $2, prints 0.
            Usage example:
              if [ "$(_version_cmp $MYVERSION 1:2.3.4-5)" -lt 0 ] ; then ...
     '''

    version1 = re.search(r'(.*):(.*)-(\w)', input_version1)

    # TODO: replace with ternary operator
    if version1:
        epoch_a = version1.group(1)
    else:
        epoch_a = -1

    non_epoch_a = re.search(r'(?:.*:)?(.*)', input_version1).group(1)
    version_a = re.search(r'([^-]*)', non_epoch_a).group(1)
    release_a = re.search(r'[^-]*-(.*)', non_epoch_a)
    if release_a:
        release_a = release_a.group(1)
    else:
        release_a = -1

    version2 = re.search(r'(.*):(.*)-(\w)', input_version2)
    if version2:
        epoch_b = version2.group(1)
    else:
        epoch_b = -1
    non_epoch_b = re.search(r'(?:.*:)?(.*)', input_version2).group(1)

    version_b = re.search(r'([^-]*)', non_epoch_b).group(1)
    release_b = re.search(r'[^-]*-(.*)', non_epoch_b)
    if release_b:
        release_b = release_b.group(1)
    else:
        release_b = -1

    epoch_comparison = version_segment_comp(str(epoch_a), str(epoch_b))
    version_comparison = version_segment_comp(str(version_a), str(version_b))
    release_comparison = version_segment_comp(str(release_a), str(release_b))
    comp_list = [epoch_comparison, version_comparison, release_comparison]
    for comp_value in comp_list:
        if comp_value != 0:
            return comp_value
    return 0

def version_segment_comp(version1, version2):
    '''
            Takes two strings, splits them on each '.' into arrays, compares
            array elements until a difference is found.

            If a third argument is specified, it will override the separator
            '.' with whatever characters were specified.

            This doesn't take into account epoch or release strings (":" or
            "-" segments).  If you want to compare versions in the format of
            "1:2.3-4", use _version_cmp(), which calls this function.

            If the values for both array elements are purely numeric, a
            numeric compare is done (to handle problems such as 9 > 10 or
            02 < 1 in a string compare), but if either value contains a
            non-numeric value or is null a string compare is done.  Null
            values are considered less than zero.

            If $1 > $2, prints 1.  If $1 < $2, prints -1.  If $1 = $2, prints 0.

            Usage example:
              if [ "$(_version_segment_cmp $MYVERSION 1.2.3)" -lt 0 ] ; then ...
      '''

    version1 = re.sub(r'\.', r' ', version1)
    version1 = version1.split()

    version2 = re.sub(r'\.', r' ', version2)
    version2 = version2.split()

    version_length = max(len(version1), len(version2))

    for i in range(version_length):
        try:
            if not version1[i].isdigit() or not version2[i].isdigit():
                if version1[i].lower() > version2[i].lower():
                    return 1
                elif version1[i].lower() < version2[i].lower():
                    return -1
            else:
                if version1[i] > version2[i]:
                    return 1
                elif version1[i] < version2[i]:
                    return -1
        except IndexError:
            if version1 > version2:
                return 1
            else:
                return 0
    else:
        return 0

def check_version_atleast(version1, version2):
    '''
            Takes the following arguments:
              $1: a string containing the version to test
              $2: the minimum acceptable version

            Returns 0 if the first argument is greater than or equal to the
            second and 1 otherwise.

            Returns 255 if called with less than two arguments.
    '''
    if version_comp(version1, version2) >= 0:
        return 0
    else:
        return 1

def check_version_helper(current_version, min_version, max_version=None):
    if not max_version:
        return check_version_atleast(current_version, min_version)
    else:
        return check_version_between(current_version, min_version, max_version)


def check_version_between(current_version, min_version, max_version):
    '''
          Takes the following arguments:
          $1: a string containing the version to test
          $2: the minimum acceptable version
          $3: the maximum acceptable version

        Returns 0 if the tested version is in the acceptable range
        (greater than or equal to the second argument, and less than or
        equal to the third), and 1 otherwise.

        Returns 255 if called with less than three arguments.
    '''
    if version_comp(current_version, min_version) >= 0 and version_comp(current_version, max_version) <= 0:
        return 0
    else:
        return 1

def check_for_acceptible_version(binary_file_name, min_version, max_version=None, version_command = "--version"):
    '''
        This is the most commonly used "public" version checking
        routine.  It delegates to check_version_helper() for the actual
        comparison, which in turn delegates to other functions in a chain.

        Arguments:
          $1: a string containing executable to call with the argument
              "--version" or "-version" to find the version to check against
          $2: the minimum acceptable version string
          $3 (optional): the maximum acceptable version string

        Returns 0 if the detected version is within the specified
        bounds, or if there were not even two arguments passed.

        Returns 1 if the detected version is not within the specified
        bounds.

        Returns 2 if running the specified command with "--version" or
        "-version" as an argument results in an error for both
        (i.e. because the command could not be found, or because neither
                "--version" nor "-version" is a valid argument)
    '''
    found_version = subprocess.Popen(
        [binary_file_name, version_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    found_version.wait()
    current_version = None
    version_tuple = found_version.communicate()
    logger.debug("version_tuple: %s", version_tuple)
    found_version.wait()
    for version in version_tuple:
        version_number = re.search(r'(\d+\.+\d*\.*\d*[.-_@+#]*\d*).*', version)
        # if version_number:
        try:
            current_version = version_number.group(1)
        except AttributeError:
            print "attribute error"
            continue
        else:
            result = check_version_helper(
                current_version, min_version, max_version)
            if result is 0:
                return True
            else:
                if max_version is None:
                    print "\nThe detected version of %s %s is less than %s \n" % (binary_file_name, current_version, min_version)
                else:
                    print "\nThe detected version of %s %s is not between %s and %s \n" % (binary_file_name, current_version, min_version, max_version)
                return False

def check_version_with(program_name, version_command, min_version, max_version=None):
    '''
        This is an alternate version of check_version() (see above)
        where the second argument specifies the entire command string with
        all arguments, pipes, etc. needed to result in a version number
        to compare.

        Arguments:
          $1: a string containing the name of the program version to
              check (this is only used in debugging output)
          $2: the complete command to be passed to eval to produce the
              version string to test
          $3: the minimum acceptable version string
          $4 (optional): the maximum acceptable version string

        Returns 0 if the detected version is within the specified
        bounds, or if at least three arguments were not passed

        Returns 1 if the detected version is not within the specified
        bounds.

        Returns 2 if running the specified command results in an error
    '''
    command_list = version_command.split()
    found_version = subprocess.Popen(
        command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version_tuple = found_version.communicate()
    for version in version_tuple:
        version = version.strip()
        version_number = re.search(r'(\d+\.+\d*\.*\d*[.-_@+#]*\d*).*', version)
        try:
            current_version = version_number.group(1)
        except AttributeError:
            print "attribute error"
            continue
        else:
            result = check_version_helper(
                current_version, min_version, max_version)
        if result is 0:
            return result
        else:
            if max_version is None:
                print "\nThe detected version of %s %s is less than %s \n" % (program_name, current_version, min_version)
            else:
                print "\nThe detected version of %s %s is not between %s and %s \n" % (program_name, current_version, min_version, max_version)
            return 1

def check_module_version(module_name, min_version):
    '''
        Checks the version of a given python module.

        Arguments:
        module_name: a string containing the name of a module that will have it's version checked
        min_version: the minimum acceptable version string
    '''
    try:
        module_version = __import__(module_name).__version__
    except (AttributeError, ImportError) as e:
        print "error: ", e
    else:
        result = check_version_helper(
            module_version, min_version)
        if result is 0:
            return result
        else:
            print "\nThe detected version of %s %s is less than %s \n" % (module_name, module_version, min_version)
        return 1

# TODO: implement and test
def get_current_esgf_library_version(library_name):
    '''
        Some ESGF components, such as esgf-security, don't actually
        install a webapp or anything that carries an independent
        manifest or version command to check, so they must be checked
        against the ESGF install manifest instead.
    '''
    version_number = ""
    if not os.path.isfile("/esg/esgf-install-manifest"):
        return 1
    else:
        with open("/esg/esgf-install-manifest", "r") as manifest_file:
            for line in manifest_file:
                line = line.rstrip() # remove trailing whitespace such as '\n'
                version_number = re.search(r'(library)\w+', line)
        if version_number:
            print "version number: ", version_number
            return version_number
        else:
            return 1

def get_current_webapp_version(webapp_name, version_command = None):
    version_property = esg_bash2py.Expand.colonMinus(version_command, "Version")
    print "version_property: ", version_property
    reg_ex = r"^(" + re.escape(version_property) + ".*)"
    with open(config.config_dictionary["tomcat_install_dir"]+"/webapps/"+webapp_name+"/META-INF/MANIFEST.MF", "r") as manifest_file:
            for line in manifest_file:
                line = line.rstrip() # remove trailing whitespace such as '\n'
                version_number = re.search(reg_ex, line)
                if version_number != None:
                    name, version = version_number.group(1).split(":")
                    return version.strip()
    return 1


def check_webapp_version(webapp_name, min_version, version_command=None):
    version_property = esg_bash2py.Expand.colonMinus(version_command, "Version")
    if not os.path.isdir(config.config_dictionary["tomcat_install_dir"]+"/webapps/"+webapp_name):
        print "Web Application %s is not present or cannot be detected!" % (webapp_name)
        return 2
    else:
        current_version= str(get_current_webapp_version(webapp_name,version_property)).strip()
        if not current_version:
            print " WARNING:(2) Could not detect version of %s" % (webapp_name)
        else:
            version_comparison = check_version_helper(current_version,min_version)
            if version_comparison == 0:
                return version_comparison
            else:
                print "\nSorry, the detected version of %s %s is older than required minimum version %s \n" % (webapp_name, current_version, min_version)
                return 1
