#!/usr/bin/local/env python

import unittest
import esg_postgres
import os
import yaml
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from esg_purge import purge_postgres

with open('esg_config.yaml', 'r') as config_file:
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
        esg_postgres.stop_postgress()
        purge_postgres()
        esg_postgres.download_postgres()
        esg_postgres.start_postgres()

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

        conn2 = esg_postgres.connect_to_db("postgres","testuser")
        cur2 = conn2.cursor()
        cur2.execute("""SELECT usename FROM pg_user;""")
        users = cur2.fetchall()
        print "\nUsers: \n"
        print users
        self.assertIsNotNone(users)
        self.test_tear_down()

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
        user_list = esg_postgres.list_users(user_name="postgres", db_name="postgres")
        conn = esg_postgres.connect_to_db("postgres","postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        if "dbsuper" not in user_list:
            cur.execute("CREATE USER dbsuper with CREATEROLE superuser PASSWORD 'password';")
        if "esgcet" not in user_list:
            cur.execute("CREATE USER esgcet PASSWORD 'password';")
            cur.execute("CREATE DATABASE esgcet;")
            cur.execute("GRANT dbsuper TO esgcet;")
        conn.commit()
        conn.close()

        conn2 = esg_postgres.connect_to_db("esgcet", db_name="esgcet", host='localhost', password='password')
        cur2 = conn2.cursor()
        try:
            cur2.execute("SELECT table_schema,table_name FROM information_schema.tables ORDER BY table_schema,table_name;")
            tables = cur2.fetchall()
            before_tables_list = [table[1]  for table in tables if table[0] == 'public']
            print "tables before:", before_tables_list
            print "tables before length:", len(before_tables_list)

            cur2.execute(open("sqldata/esgf_esgcet.sql", "r").read())

            cur2.execute("SELECT table_schema,table_name FROM information_schema.tables ORDER BY table_schema,table_name;")
            tables = cur2.fetchall()
            after_tables_list = [table[1] for table in tables if table[0] == 'public']
            print "tables after:", after_tables_list
            print "tables after length:", len(after_tables_list)
        except Exception, error:
            print 'error:', error

        schemas_list = esg_postgres.postgres_list_db_schemas(conn=conn2)
        print "schemas_list before:", schemas_list
        cur2.execute(open("sqldata/esgf_node_manager.sql", "r").read())
        schemas_list = esg_postgres.postgres_list_db_schemas(conn=conn2)
        print "schemas_list after:", schemas_list
        self.assertTrue("esgf_node_manager" in schemas_list)

        cur2.execute(open("sqldata/esgf_security.sql", "r").read())
        schemas_list = esg_postgres.postgres_list_db_schemas(conn=conn2)
        print "schemas_list after:", schemas_list
        self.assertTrue("esgf_security" in schemas_list)

        cur2.execute(open("sqldata/esgf_dashboard.sql", "r").read())
        schemas_list = esg_postgres.postgres_list_db_schemas(conn=conn2)
        print "schemas_list after:", schemas_list
        self.assertTrue("esgf_dashboard" in schemas_list)
        self.assertIsNotNone(after_tables_list)

        # user_list = esg_postgres.list_users(conn=conn2)
        # print "user_list before load_esgf_data:", user_list
        # esg_postgres.load_esgf_data(cur2)
        cur2.execute(open("sqldata/esgf_security_data.sql", "r").read())
        roles_list = esg_postgres.list_roles(conn=conn2)
        print "roles_list after load_esgf_data:", roles_list
        cur2.execute("SELECT table_schema,table_name FROM information_schema.tables ORDER BY table_schema,table_name;")
        tables = cur2.fetchall()
        after_tables_list = [table[1] for table in tables if table[0] == 'public']
        print "tables after esgf_security_data:", after_tables_list

        databases = esg_postgres.postgres_list_dbs(conn2)
        print "databases after esgf_security_data:", databases
        # self.assertTrue("admin" in roles_list)
        # conn2.close()

        self.test_tear_down()

    def test_create_pg_pass_file(self):
        esg_postgres.create_pg_pass_file()
        self.assertTrue(os.path.isfile(os.path.join(os.environ["HOME"], ".pgpass")))


    def test_build_connection_string(self):
        test_connection_string = esg_postgres.build_connection_string("postgres", db_name="postgres", host="localhost")
        print "test_connection_string:", test_connection_string
        self.assertIsNotNone(test_connection_string)




if __name__ == '__main__':
    unittest.main()
