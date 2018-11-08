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


        print()
        print()
        print()
        print()
        print("---------------------------------------------------")
        print("RUNNING: flake8 on directory %s" % base_path)
        print("---------------------------------------------------")
        print()
        print()
        print()
        print()
        cmd = "flake8 --show-source --statistics " +\
              "--max-line-length=120 %s" % (base_path)
        P = subprocess.Popen(shlex.split(cmd),
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out,e = P.communicate()
        out = out.decode("utf-8")
        if out != "":
            print(out)
        self.assertEqual(out, "")


if __name__ == '__main__':
    unittest.main(verbosity=2)
