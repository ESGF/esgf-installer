import unittest
import os
import shutil
import logging
from context import esgf_utilities
from context import base
from context import data_node
from context import filters
from esgf_utilities import esg_bash2py
from base import esg_tomcat_manager
from data_node import orp
from filters import esg_security_tokenless_filters
import yaml


current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_Security_Tokenless_Filters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up esg_security_tokenless_filters Test Fixture"
        print "******************************* \n"

        if not os.path.exists("/usr/local/tomcat"):
            esg_tomcat_manager.main()

        try:
            shutil.rmtree("/usr/local/tomcat/webapps/thredds/WEB-INF")
        except OSError, error:
            pass

        if not os.path.exists("/usr/local/tomcat/webapps/thredds/WEB-INF/lib"):
            esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/thredds/WEB-INF/lib")


    def test_setup_security_tokenless_filters(self):
        esg_security_tokenless_filters.setup_security_tokenless_filters()
        lib_directory = "/usr/local/tomcat/webapps/thredds/WEB-INF/lib"
        orp_jar_list = esg_security_tokenless_filters.initialize_orp_jar_list()
        library_jars = esg_security_tokenless_filters.initialize_esgf_mirror_jar_list()
        
        for orp_jar in orp_jar_list:
            jar_path = os.path.join(lib_directory, orp_jar)
            self.assertTrue(os.path.exists(jar_path))




if __name__ == '__main__':
    unittest.main()
