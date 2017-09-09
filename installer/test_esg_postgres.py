#!/usr/bin/local/env python

import unittest
import esg_postgres
import os
import yaml
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_postgres(unittest.TestCase):

    # def test_check_for_postgres_db_user(self):
    #     esg_postgres.stop_postgress()
    #     esg_postgres.check_for_postgres_db_user()

    @classmethod
    def tearDownClass(cls):
        conn = esg_postgres.connect_to_db("postgres","postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("DROP USER testuser;")
        cur.execute("DROP DATABASE IF EXISTS unittestdb;")
        cur.execute("DROP USER dbsuper;")
        cur.execute("DROP USER esgcet;")
        cur.execute("DROP DATABASE IF EXISTS esgcet;")
        conn.close()

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

    def test_list_users(self):
        user_list = esg_postgres.list_users("postgres", "postgres")
        self.assertIsNotNone(user_list)

    def test_list_schemas(self):
        output = esg_postgres.postgres_list_db_schemas("postgres", "postgres")
        self.assertIsNotNone(output)

    def test_add_schema_from_file(self):
        user_list = esg_postgres.list_users("postgres", "postgres")
        conn = esg_postgres.connect_to_db("postgres","postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        if "dbsuper" not in user_list:
            cur.execute("CREATE USER dbsuper with CREATEROLE superuser PASSWORD 'password';")
        if "esgcet" not in user_list:
            cur.execute("CREATE USER esgcet PASSWORD 'password';")
            cur.execute("CREATE DATABASE esgcet;")
            cur.execute("GRANT dbsuper TO esgcet;")
        # try:
        #     #cur.execute("CREATE USER dbsuper with CREATEROLE superuser PASSWORD 'password';")
        #     #cur.execute("CREATE USER esgcet PASSWORD 'password';")
        #     #cur.execute("CREATE DATABASE esgcet;")
        #     cur.execute("GRANT dbsuper TO esgcet;")
        # except Exception, error:
        #     print "error:", error
        conn.commit()
        conn.close()

        conn2 = esg_postgres.connect_to_db("esgcet","esgcet")
        cur2 = conn2.cursor()
        try:
            # cur.execute("postgres < sqldata/esgf_esgcet.sql")
            schema_tables = esg_postgres.postgres_list_schemas_tables("esgcet", "esgcet")
            print "schema_tables after: ", schema_tables
            cur2.execute(open("sqldata/esgf_esgcet.sql", "r").read())
            output = esg_postgres.postgres_list_db_schemas("esgcet", "esgcet")
            print "output after add schema:", output
            schema_tables = esg_postgres.postgres_list_schemas_tables("esgcet", "esgcet")
            print "schema_tables after: ", schema_tables
        except Exception, error:
            print 'error:', error



if __name__ == '__main__':
    unittest.main()
