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
        esg_truststore_manager.fetch_esgf_truststore("/tmp/esg-truststore.ts", "/tmp/esgf-ca-bundle.crt", "/tmp/grid-security/certificates")
        self.assertTrue(os.path.exists("/tmp/esg-truststore.ts"))
        self.assertTrue(os.path.exists("/tmp/esgf-ca-bundle.crt"))

        os.remove("/tmp/esg-truststore.ts")
        os.remove("/etc/certs/esgf-ca-bundle.crt")


    def test_rebuild_truststore(self):
        esg_truststore_manager.rebuild_truststore("/tmp/test-truststore.ts")
        self.assertTrue(os.path.isfile("/tmp/test-truststore.ts"))

    def test_create_new_truststore(self):
        esg_truststore_manager.create_new_truststore("/tmp/new-truststore.ts")
        self.assertTrue(os.path.isfile("/tmp/new-truststore.ts"))

if __name__ == '__main__':
    unittest.main(verbosity=2)
