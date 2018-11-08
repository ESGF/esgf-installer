from __future__ import print_function
import unittest
import os
import subprocess
import shlex


class test_flake8(unittest.TestCase):

    def test_flake8(self):
        base_path = os.path.dirname(__file__)
        base_path = os.path.join(base_path, "..")
        base_path = os.path.abspath(base_path)
        dirs = ["base", "data_node", "filters", "idp_node",
                "index_node", "shell_scripts"]

        flake8_passed = True
        for p in dirs:
            path = os.path.join(base_path, p)

            print()
            print()
            print()
            print()
            print("---------------------------------------------------")
            print("RUNNING: flake8 on directory %s" % path)
            print("---------------------------------------------------")
            print()
            print()
            print()
            print()
            cmd = "flake8 --show-source --statistics " +\
                "--max-line-length=120 %s" % (path)
            P = subprocess.Popen(shlex.split(cmd),
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out,e = P.communicate()
            out = out.decode("utf-8")
            if out != "":
                print(out)
                flake8_passed = False

        self.assertEqual(flake8_passed, True)

if __name__ == '__main__':
    unittest.main(verbosity=2)
