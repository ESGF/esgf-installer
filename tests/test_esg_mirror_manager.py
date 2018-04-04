import unittest
from context import esgf_utilities
from esgf_utilities import esg_mirror_manager


class Test_ESG_MIRROR_MANAGER(unittest.TestCase):

    def test_check_mirror_connection(self):
        output = esg_mirror_manager.check_mirror_connection("devel")
        print "output:", output
        self.assertTrue(output)
        self.assertEqual(len(output), 4)

    def test_get_success_or_fail_reponses(self):
        pass

    def test_get_esgf_dist_mirror(self):
        pass


if __name__ == "__main__":
    unittest.main()
