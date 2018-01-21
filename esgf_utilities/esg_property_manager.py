'''
Property reading and writing...
'''
import os
import yaml
import logging
import ConfigParser

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

#TODO:rename config["config_file"] to config["property_file"]
def get_property(property_name, config_file=config["config_file"], section_name="installer_properties"):
    '''
        Gets a single property from the config_file using ConfigParser
        arg 1 - the string that you wish to get the property of (and make a variable)
        arg 2 - the path to the config file
    '''
    parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    parser.read(config_file)
    try:
        return parser.get(section_name, property_name)
    except ConfigParser.NoSectionError:
        logger.debug("could not find property %s", property_name)
    except ConfigParser.NoOptionError:
        logger.debug("could not find property %s", property_name)


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
        logger.debug("section already exists")

    parser.set('installer_properties', property_name, property_value)
    with open(config_file, "w") as config_file_object:
        parser.write(config_file_object)
