'''
Property reading and writing...
'''
import os
import re
import yaml
import esg_logging_manager
import esg_env_manager
import ConfigParser


logger = esg_logging_manager.create_rotating_log(__name__)

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)

def get_property(property_name, config_file=config["config_file"]):
    '''
        Gets a single property from the config_file using ConfigParser
        arg 1 - the string that you wish to get the property of (and make a variable)
        arg 2 - the path to the config file
    '''
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_file)
    try:
        return parser.get("installer_properties", property_name)
    except ConfigParser.NoSectionError, error:
        print "could not find property: {property_name}".format(property_name=property_name)
    except ConfigParser.NoOptionError, error:
        print "error:", error

# TODO: Can't find usage anywhere; maybe deprecate
def get_property_as():
    '''
        Gets a single property from the arg string and turns the alias into a
        shell var assigned to the value fetched.
        arg 1 - the string that you wish to get the property of (and make a variable)
        arg 2 - the alias string value of the variable you wish to create and assign
        arg 3 - the optional default value if no value is found for arg 1
    '''
    pass

# TODO: Can't find usage anywhere; maybe deprecate
def remove_property(key):
    '''
        Removes a given variable's property representation from the property file
    '''
    print "removing %s's property from %s" % (key, config["config_file"])
    property_found = False
    datafile = open(config["config_file"], "r+")
    searchlines = datafile.readlines()
    datafile.seek(0)
    for line in searchlines:
        if key not in line:
            datafile.write(line)
        else:
            property_found = True
    datafile.truncate()
    datafile.close()
    return property_found


def write_as_property(property_name, property_value=None, config_file=config["config_file"]):
    '''
        Writes variable out to property file using ConfigParser
        arg 1 - The string of the variable you wish to write as property to property file
        arg 2 - The value to set the variable to (default: None)
    '''
    parser = ConfigParser.SafeConfigParser()
    parser.read(config_file)
    try:
        parser.add_section("installer_properties")
    except ConfigParser.DuplicateSectionError:
        print "section already exists"

    parser.set('installer_properties', property_name, property_value)
    with open(config_file, "w") as config_file_object:
        parser.write(config_file_object)
