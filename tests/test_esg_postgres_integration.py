import unittest
import os
from base import esg_postgres
import yaml
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from context import esgf_utilities
from esgf_utilities.esg_purge import purge_postgres
from esgf_utilities import esg_bash2py

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

class test_ESG_postgres_integration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Postgres Test Fixture"
        print "******************************* \n"
        esg_postgres.stop_postgress()
        purge_postgres()
        esg_bash2py.mkdir_p(config["esg_config_dir"])

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



if __name__ == '__main__':
    unittest.main()
