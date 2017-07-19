import sys
import subprocess
import logging
import yaml
import esg_bash2py
import esg_logging_manager

logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

#----------------------------------------------------------
# Environment Management Utility Functions
#----------------------------------------------------------
def remove_env(env_name):
    print "removing %s's environment from %s" % (env_name, config["envfile"])
    found_in_env_file = False
    datafile = open(config["envfile"], "r+")
    searchlines = datafile.readlines()
    datafile.seek(0)
    for line in searchlines:
        if env_name not in line:
            datafile.write(line)
        else:
            found_in_env_file = True
    datafile.truncate()
    datafile.close()
    return found_in_env_file

#TODO: Fix sed statement
def remove_install_log_entry(entry):
    print "removing %s's install log entry from %s" % (entry, config["install_manifest"])
    subprocess.check_output("sed -i '/[:]\?'${key}'=/d' ${install_manifest}")

def deduplicate_settings_in_file(envfile = None):
    '''
    Environment variable files of the form
    Ex: export FOOBAR=some_value
    Will have duplcate keys removed such that the
    last entry of that variable is the only one present
    in the final output.
    arg 1 - The environment file to dedup.
    '''

    infile = esg_bash2py.Expand.colonMinus(envfile, config["envfile"])
    try:
        my_set = set()
        deduplicated_list = []
        with open(infile, 'r+') as environment_file:
            env_settings = environment_file.readlines()

            for setting in reversed(env_settings):
                # logger.debug(setting.split("="))
                key, value = setting.split("=")
                # logger.debug("key: %s", key)
                # logger.debug("value: %s", value)

                if key not in my_set:
                    deduplicated_list.append(key+ "=" + value)
                    my_set.add(key)
            deduplicated_list.reverse()
            # logger.debug("deduplicated_list: %s", str(deduplicated_list))
            environment_file.seek(0)
            for setting in deduplicated_list:
                environment_file.write(setting)
            environment_file.truncate()
    except IOError, error:
        logger.error(error)
        sys.exit(0)


def deduplicate_properties(properties_file = None):
    infile = esg_bash2py.Expand.colonMinus(properties_file, config["config_file"])
    try:
        my_set = set()
        deduplicated_list = []
        with open(infile, 'r+') as prop_file:
            property_settings = prop_file.readlines()
            for prop in reversed(property_settings):
                if not prop.isspace():
                    key, value = prop.split("=")
                    # logger.debug("key: %s", key)
                    # logger.debug("value: %s", value)
                if key not in my_set:
                    deduplicated_list.append(key+ "=" + value)
                    my_set.add(key)
            deduplicated_list.reverse()
            # logger.debug("deduplicated_list: %s", str(deduplicated_list))
            prop_file.seek(0)
            for setting in deduplicated_list:
                prop_file.write(setting)
            prop_file.truncate()
    except IOError, error:
        logger.error(error)
        sys.exit(0)

#TODO: fix awk statements
# def get_config_ip(interface_value):
#     '''
#     #####
#     # Get Current IP Address - Needed (at least temporarily) for Mesos Master
#     ####
#     Takes a single interface value
#     "eth0" or "lo", etc...
#     '''
    # return subprocess.check_output("ifconfig $1 | grep \"inet[^6]\" | awk '{ gsub (\" *inet [^:]*:\",\"\"); print $1}'")
