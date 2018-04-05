import unittest
from context import esgf_utilities
from esgf_utilities import esg_mirror_manager


class Test_ESG_MIRROR_MANAGER(unittest.TestCase):

    def test_check_mirror_connection(self):
        output = esg_mirror_manager.check_mirror_connection("devel")
        print "output:", output
        self.assertTrue(output)
        self.assertEqual(len(output), 4)

    def test_find_fastest_mirror(self):
        output = esg_mirror_manager.find_fastest_mirror("devel")
        print "output:", output
        self.assertTrue(output)
    def test_get_mirror_response_times(self):
        output = esg_mirror_manager.get_mirror_response_times()
        print "response times:", output
        self.assertTrue(output)

    def test_get_esgf_dist_mirror(self):
        pass


if __name__ == "__main__":
    unittest.main()
