'''
Property reading and writing...
'''
import os
import logging
import ConfigParser
import yaml
from backports import configparser

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def get_property(property_name, property_file=config["property_file"], section_name="installer.properties", separator="."):
    '''
        Gets a single property from the property_file using ConfigParser
        arg 1 - the string that you wish to get the property of (and make a variable)
        arg 2 - the path to the config file
    '''
    property_name = property_name.replace("_", separator)
    parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    parser.read(property_file)
    try:
        value = parser.get(section_name, property_name)
        if value is None or value == "":
            raise ConfigParser.NoOptionError(property_name, section_name)
        return value
    except ConfigParser.NoSectionError:
        logger.debug("Could not find section: %s", section_name)
        raise
    except ConfigParser.NoOptionError:
        logger.debug("Could not find property or property has no value: %s", property_name)
        raise

def set_property(property_name, property_value=None, property_file=config["property_file"], section_name="installer.properties", separator="."):
    '''
        Writes variable out to property file using ConfigParser
        arg 1 - The string of the variable you wish to write as property to property file
        arg 2 - The value to set the variable to (default: None)
    '''
    property_name = property_name.replace("_", separator)
    parser = configparser.ConfigParser()
    parser.read(property_file)
    if section_name not in parser:
        parser[section_name] = {}
    parser[section_name][property_name] = property_value
    parser.write(space_around_delimiters=False)
