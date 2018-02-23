#!/usr/bin/local/env python

import unittest
import os
import yaml
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from context import esgf_utilities
from context import base
from base import esg_postgres
from esgf_utilities.esg_exceptions import SubprocessError
from esgf_utilities.esg_purge import purge_postgres

current_directory = os.path.join(os.path.dirname(__file__))

with open(os.path.join(current_directory, os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

class test_ESG_postgres(unittest.TestCase):

    # def test_check_for_postgres_db_user(self):
    #     esg_postgres.stop_postgress()
    #     esg_postgres.check_for_postgres_db_user()

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Postgres Test Fixture"
        print "******************************* \n"
        try:
            esg_postgres.stop_postgress()
        except SubprocessError, error:
            pass
        purge_postgres()
        esg_postgres.download_postgres()
        esg_postgres.start_postgres()
        esg_postgres.setup_hba_conf_file()
        esg_postgres.restart_postgres()

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Tearing down ESGF Postgres Test Fixture"
        print "******************************* \n"
        conn = esg_postgres.connect_to_db("postgres","postgres")
        #Tests have already been cleaned up with self.test_setup()
        if not conn:
            return
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("DROP USER IF EXISTS testuser;")
        cur.execute("DROP DATABASE IF EXISTS esgcet;")
        cur.execute("DROP USER IF EXISTS dbsuper;")
        cur.execute("DROP USER IF EXISTS esgcet;")
        cur.execute("DROP DATABASE IF EXISTS unittestdb;")
        conn.close()
        purge_postgres()

    def test_setup(self):
        print "\n*******************************"
        print "Setting up ESGF Postgres Test Fixture"
        print "******************************* \n"
        esg_postgres.stop_postgress()
        purge_postgres()
        esg_postgres.download_postgres()
        esg_postgres.start_postgres()

    def test_tear_down(self):
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

    def test_connect_to_db(self):
        conn = esg_postgres.connect_to_db("postgres","postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        try:
            cur.execute("CREATE DATABASE unittestdb;")
        except Exception, error:
            print "error:", error
        cur.execute("""SELECT datname from pg_database;""")
        rows = cur.fetchall()
        print "\nRows: \n"
        print rows
        self.assertIsNotNone(rows)
        conn.close()

    def test_add_user_to_db(self):
        conn = esg_postgres.connect_to_db("postgres","postgres")
        cur = conn.cursor()
        try:
            cur.execute("CREATE USER testuser with CREATEROLE superuser PASSWORD 'password';")
        except Exception, error:
            print "error:", error
        conn.commit()
        conn.close()
        cur.close()

        conn2 = esg_postgres.connect_to_db("testuser",db_name="postgres", password='password')
        cur2 = conn2.cursor()
        cur2.execute("""SELECT usename FROM pg_user;""")
        users = cur2.fetchall()
        print "\nUsers: \n"
        print users
        self.assertIsNotNone(users)
        conn2.close()
        cur2.close()
        # self.test_tear_down()

    def test_list_users(self):
        user_list = esg_postgres.list_users(user_name="postgres", db_name="postgres")
        self.assertIsNotNone(user_list)

        conn = esg_postgres.connect_to_db("postgres","postgres")
        user_list = esg_postgres.list_users(conn=conn)
        self.assertIsNotNone(user_list)

    def test_list_schemas(self):
        output = esg_postgres.postgres_list_db_schemas(user_name="postgres", db_name="postgres")
        self.assertIsNotNone(output)

        conn = esg_postgres.connect_to_db("postgres","postgres")
        schemas_list = esg_postgres.postgres_list_db_schemas(conn=conn)
        print "schemas_list:", schemas_list
        self.assertIsNotNone(schemas_list)

    def test_add_schema_from_file(self):
        esg_postgres.setup_db_schemas(False, publisher_password="changeit")
        db_schemas = esg_postgres.postgres_list_db_schemas(user_name="dbsuper", db_name="esgcet", password="changeit")
        print "db_schemas:", db_schemas
        self.assertTrue("esgf_security" in db_schemas)

    def test_create_pg_pass_file(self):
        esg_postgres.create_pg_pass_file()
        self.assertTrue(os.path.isfile(os.path.join(os.environ["HOME"], ".pgpass")))


    def test_build_connection_string(self):
        test_connection_string = esg_postgres.build_connection_string("postgres", db_name="postgres", host="localhost")
        print "test_connection_string:", test_connection_string
        self.assertIsNotNone(test_connection_string)




if __name__ == '__main__':
    unittest.main()
