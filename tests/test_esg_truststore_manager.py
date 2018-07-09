import unittest
import logging
import os
import shutil
from context import esgf_utilities
from esgf_utilities import pybash, esg_truststore_manager
import yaml

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

logger = logging.getLogger("esgf_logger" + "." + __name__)

class test_ESG_truststore_manager(unittest.TestCase):


    def test_fetch_esgf_certificates(self):
        esg_truststore_manager.fetch_esgf_certificates("/tmp/grid-security/certificates")
        self.assertTrue(os.path.exists("/tmp/grid-security/certificates/0119347c.0"))

        shutil.rmtree("/tmp/grid-security/certificates")


    def test_fetch_esgf_truststore(self):
        esg_truststore_manager.fetch_esgf_truststore("/tmp/esg-truststore.ts")
        self.assertTrue(os.path.exists("/etc/certs/esgf-ca-bundle.crt"))

        os.remove("/etc/certs/esgf-ca-bundle.crt")

if __name__ == '__main__':
    unittest.main(verbosity=2)
