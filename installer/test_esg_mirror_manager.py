from esg_mirror_manager import *
import unittest

class Test_ESG_MIRROR_MANAGER(unittest.TestCase):

    def text_check_mirror_connection(self):
        response = generate_response_array('devel')
        print "response:", response

        for key,value in response.items():
            print "value type:", type(value)
            print "status_code:", type(value.status_code)
            self.assertEqual(value.status_code, 200)

    def test_get_success_or_fail_reponses(self):
        pass

    def test_get_esgf_dist_mirror(self):
        pass




if __name__ == "__main__":
	unittest.main()







