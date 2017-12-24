import unittest
import esg_postgres
import os
import yaml
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from esg_purge import purge_postgres

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_postgres_integration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Postgres Test Fixture"
        print "******************************* \n"
        esg_postgres.stop_postgress()
        purge_postgres()

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
<<<<<<< HEAD
        esg_postgres.setup_postgres()
=======
        esg_postgres.setup_postgres(backup_existing_db="N", default_continue_install = "Y")

>>>>>>> python_master


if __name__ == '__main__':
    unittest.main()
