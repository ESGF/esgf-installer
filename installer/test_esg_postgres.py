#!/usr/bin/local/env python

import unittest
import esg_postgres
import os
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_postgres(unittest.TestCase):

    def test_check_postgress_process(self):
        esg_postgres.stop_postgress()
        output = esg_postgres.check_postgress_process()
        self.assertEqual(output, 1)

        esg_postgres.start_postgress()
        output = esg_postgres.check_postgress_process()
        self.assertEqual(output, 0)



if __name__ == '__main__':
    unittest.main()
