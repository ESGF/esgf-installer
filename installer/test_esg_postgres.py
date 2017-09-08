#!/usr/bin/local/env python

import unittest
import esg_postgres
import os
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_postgres(unittest.TestCase):

    # def test_check_for_postgres_db_user(self):
    #     esg_postgres.stop_postgress()
    #     esg_postgres.check_for_postgres_db_user()

    def test_connect_to_db(self):
        conn = esg_postgres.connect_to_db("postgres","postgres")
        cur = conn.cursor()
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
        rows = cur2.fetchall()
        print "\nUsers: \n"
        print rows
        self.assertIsNotNone(rows)

if __name__ == '__main__':
    unittest.main()
