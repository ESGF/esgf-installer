'''
Property reading and writing...
'''
import os
import logging
import ConfigParser
import yaml
from configobj import ConfigObj

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def build_prompt(msg=None, default=None, choices=None, not_none=True):

    if default is None and not_none:
        prompt_str = "{}: ".format(msg)
    elif choices is None:
        prompt_str = "{} [{}]: ".format(msg, default)
    else:
        choice_str = "({})".format("|".join(choices))
        prompt_str = "{} {} [{}]: ".format(msg, choice_str, default)

    return prompt_str

def _validate(value, choices=None, not_none=True):
    if choices is not None:
        if value not in choices:
            print "{} not in choices".format(value)
            return False
    if not_none:
        if value is None:
            print "Input cannot be None"
            return False
    return True

def clean(value):

    if value is not None:
        return value.strip()
    return value

def _prompt(key, msg=None, default=None, choices=None, not_none=True):

    prompt_str = build_prompt(msg, default, choices, not_none)
    # Get input and check if it is valid
    is_valid = False
    while not is_valid:
        new_value = raw_input(prompt_str) or default
        new_value = clean(new_value)
        is_valid = _validate(new_value, choices, not_none)

    # Do something with the new value
    return new_value

def get_yes_no_property(key, prompt=None, default="no"):

    default = default.strip().lower()
    new_value = get_property(key, prompt, default=default, choices=["y", "n", "yes", "no"])
    return new_value.lower().startswith('y')

def get_property(key, prompt=None, default=None, choices=None, not_none=True):

    separator = "."
    section = "installer.properties"
    key = key.replace("_", separator)
    try:
        new_value = read_config(key, section, config["property_file"], not_none=not_none)
        new_value = clean(new_value)
        if prompt is not None and not _validate(new_value, choices, not_none):
            new_value = _prompt(key, prompt, default, choices, not_none)
            set_property(key, new_value)
    except ConfigParser.NoOptionError:
        new_value = None
        if prompt is not None:
            new_value = _prompt(key, prompt, default, choices, not_none)
            set_property(key, new_value)

    return new_value

def set_property(key, value, separator="."):

    key = key.replace("_", separator)
    write_config(key, value, "installer.properties", config["property_file"])

def read_config(key, section, filename, not_none=True):

    parser = ConfigParser.SafeConfigParser(allow_no_value=True)
    parser.read(filename)
    try:
        value = parser.get(section, key)
        if not_none and (value is None or value == ""):
            raise ConfigParser.NoOptionError(key, section)
        logger.info("%s = %s", key, value)
        return value
    except ConfigParser.NoSectionError:
        logger.debug("Could not find section: %s", section)
        raise
    except ConfigParser.NoOptionError:
        logger.debug("Could not find property or property has no value: %s", key)
        raise

def write_config(key, value, section, filename):

    parser = ConfigObj(filename)
    if section not in parser:
        parser[section] = {}
    parser[section][key] = value
    parser.write()
    logger.info("Set property: %s = %s", key, value)
