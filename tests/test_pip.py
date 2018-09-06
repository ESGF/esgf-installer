import unittest
from context import esgf_utilities
from esgf_utilities import esg_functions

class test_Pip(unittest.TestCase):

    def test_pip(self):
        pkg = "somepackage"
        repo = "https://github.com/bast/somepackage.git"
        version = "1.2.3"

        cur_version = esg_functions.pip_version(pkg)
        self.assertTrue(cur_version is None)

        esg_functions.pip_install(pkg+"=="+version)
        cur_version = esg_functions.pip_version(pkg)
        self.assertTrue(cur_version == version)

        esg_functions.call_binary("pip", ["uninstall", "-y", pkg])
        cur_version = esg_functions.pip_version(pkg)
        self.assertTrue(cur_version is None)

        esg_functions.pip_install_git(repo, pkg)
        cur_version = esg_functions.pip_version(pkg)
        self.assertTrue(cur_version == version)

        esg_functions.call_binary("pip", ["uninstall", "-y", pkg])
        cur_version = esg_functions.pip_version(pkg)
        self.assertTrue(cur_version is None)

if __name__ == '__main__':
    unittest.main()
