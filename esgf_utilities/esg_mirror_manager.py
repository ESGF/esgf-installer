'''
ESGF Distribution Mirrors Utilities
'''
import os
import re
import logging
from collections import OrderedDict
import requests
import yaml

logger = logging.getLogger("esgf_logger" +"."+ __name__)

with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

# List of mirror location

esgf_dist_mirrors_list = ("http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist", "http://dist.ceda.ac.uk/esgf/dist", "http://aims1.llnl.gov/esgf/dist", "http://esg-dn2.nsc.liu.se/esgf/dist", "https://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist", "https://dist.ceda.ac.uk/esgf/dist", "https://aims1.llnl.gov/esgf/dist", "https://esg-dn2.nsc.liu.se/esgf/dist")

def check_mirror_connection(install_type):
    """ Check if mirrors are accessible."""
    response_array = {}
    for mirror in esgf_dist_mirrors_list:
        if install_type == "devel":
            try:
                mirror_response = requests.get('{}/devel/lastpush.md5'.format(mirror), timeout=4.0).text
                response_array[mirror] = mirror_response.split()[0]
            except requests.exceptions.Timeout:
                logger.warn("%s requests timed out", mirror)
        else:
            try:
                mirror_response = requests.get('{}/lastpush.md5'.format(mirror), timeout=4.0).text
                response_array[mirror] = mirror_response.split()[0]
            except requests.exceptions.Timeout:
                logger.warn("%s requests timed out", mirror)

    return response_array

def get_mirror_response_times():
    """ Return a dictionary tuple with successful and
    unsuccessful response times from mirrors.
    """
    response_times = {} # Successful connections
    failed_requests = {} # Unsuccessful connection

    for mirror in esgf_dist_mirrors_list:
        logger.debug("mirror: %s", mirror)

        try:
            response = requests.get(mirror, timeout=4.0)
            logger.debug("%s response time %s", mirror, response.elapsed)
            response_times[mirror] = response.elapsed
        except requests.exceptions.Timeout:
            logger.warn("%s request timed out", mirror)
            failed_requests[mirror] = "Request timed out"
        except requests.exceptions.ConnectionError, error:
            logger.warn(error)
            failed_requests[mirror] = "Unable to connect to mirror"


    return (response_times, failed_requests)

def rank_response_times(response_times):
    """ Sort the response time of mirrors and return a list of them."""
    return OrderedDict(sorted(response_times.items(), key=lambda x: x[1]))

def get_lastpush_md5(mirror, install_type):
    '''Gets the lastpush.md5 file from the specified mirror.  Can be used to check if mirror is in sync with the master mirror'''
    if install_type == "devel":
        mirror_md5_url = 'http://{}/dist/devel/lastpush.md5'.format(mirror)
    else:
        mirror_md5_url = 'http://{}/dist/lastpush.md5'.format(mirror)

    mirror_response = requests.get(mirror_md5_url, timeout=4.0).text
    mirror_md5 = mirror_response.split()[0]

    return mirror_md5

def check_mirror_congruency(mirror_md5, master_mirror_md5):
    '''Check if mirrors are synced'''
    if mirror_md5 == master_mirror_md5:
        return True

def find_fastest_mirror(install_type):
    '''Find the mirror with the fastest response time'''
    response_times, _ = get_mirror_response_times()
    ranked_response_times = rank_response_times(response_times)

    master_mirror = 'distrib-coffee.ipsl.jussieu.fr/pub/esgf'
    if ranked_response_times.items()[0][0] == master_mirror:
        logger.debug("Master mirror is fastest")
        return master_mirror

    master_mirror_md5 = get_lastpush_md5(master_mirror, install_type)

    for mirror in ranked_response_times:
        if mirror == master_mirror:
            continue
        logger.debug("mirror: %s", mirror)
        mirror_md5 = get_lastpush_md5(mirror, install_type)
        if check_mirror_congruency(mirror_md5, master_mirror_md5):
            return mirror
        else:
            logger.info("%s is out of sync with the master mirror", mirror)

    return master_mirror

def select_dist_mirror():
    """ Return the nearest mirror available. """
    response_times, _ = get_mirror_response_times()

    # Order the response time of the mirrors
    ranked_response_times = rank_response_times(response_times)
    logger.debug("ranked_response_times: %s", ranked_response_times)

    while True:
        try:
            _render_distribution_mirror_menu(ranked_response_times)
            choice = _select_distribution_mirror()
            logger.debug("choice result: %s", ranked_response_times.items()[choice][0])
            return ranked_response_times.items()[choice][0]
        except IndexError:
            logger.error("Invalid selection", exc_info=True)
            continue
        break

def is_valid_mirror(mirror_url):
    '''Checks if the mirror_url is in the valid set of distribution mirrors'''
    mirror_base_url = re.sub(r'\/\d\.\d', '', mirror_url)
    logger.debug("mirror_base_url: %s", mirror_base_url)
    if mirror_base_url not in esgf_dist_mirrors_list:
        logger.error("%s is not a valid distribution mirror url", mirror_base_url)
        return
    return True

def _render_distribution_mirror_menu(distribution_mirror_choices):
    """ Display the mirrors from fastest (1) to slowest (4)."""
    print "Please select the ESGF distribution mirror for this installation (fastest to slowest): \n"
    print "\t-------------------------------------------\n"
    for index, (key, _) in enumerate(distribution_mirror_choices.iteritems(), 1):
        print "\t %i) %s" % (index, key)
    print "\n\t-------------------------------------------\n"

def _select_distribution_mirror():
    """ Return the user selected mirror."""
    choice = int(raw_input("Enter mirror number: "))
    #Accounts for off by 1 error
    while choice >= 5 and choice <= 0:
        print "The selected mirror number does not exist."
        choice = int(raw_input("Enter mirror number: "))
    choice = choice - 1
    return choice
