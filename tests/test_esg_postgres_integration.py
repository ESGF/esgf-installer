import unittest
import os
import ConfigParser
import re
import yaml
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from context import esgf_utilities
from context import base
from base import esg_postgres
from esg_purge import purge_postgres
from esgf_utilities import pybash, esg_functions

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

class test_ESG_postgres_integration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Postgres Test Fixture"
        print "******************************* \n"
        esg_postgres.stop_postgres()
        purge_postgres()
        pybash.mkdir_p(config["esg_config_dir"])

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Tearing down ESGF Postgres Test Fixture"
        print "******************************* \n"
        conn = esg_postgres.connect_to_db("postgres","postgres")
        users_list = esg_postgres.list_users(conn=conn)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("DROP USER IF EXISTS testuser;")
        # if "testuser" in users_list:
        #     cur.execute("DROP USER testuser;")
        if "dbsuper" in users_list:
            cur.execute("DROP USER dbsuper;")
        if "esgcet" in users_list:
            cur.execute("DROP USER esgcet;")
        cur.execute("DROP DATABASE IF EXISTS unittestdb;")
        cur.execute("DROP DATABASE IF EXISTS esgcet;")
        conn.close()
        purge_postgres()


    def test_setup_postgres(self):
        '''Tests the entire postgres setup; Essentially an integration test'''
        esg_postgres.setup_postgres(default_continue_install = "Y")
        postgres_version_found = esg_functions.call_subprocess("psql --version")["stdout"]
        postgres_version_number = re.search("\d.*", postgres_version_found).group()
        self.assertTrue("8.4.20" == postgres_version_number)
        parser = ConfigParser.ConfigParser()
        parser.read("/esg/config/esgf.properties")
        self.assertTrue("installer.properties", "db.user")
        self.assertTrue("installer.properties", "db.host")
        self.assertTrue("installer.properties", "db.database")




if __name__ == '__main__':
    unittest.main()
