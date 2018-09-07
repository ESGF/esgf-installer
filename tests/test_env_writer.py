import unittest
import os
from context import esgf_utilities
ENVFILE = "/tmp/sample.env"
class test_env_write(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(ENVFILE)
        except OSError:
            pass

    def export_in_second_file(self):
        from esgf_utilities.esg_env_manager import _EnvWriter
        EnvWriter = _EnvWriter(ENVFILE)
        EnvWriter.export("BAR", "bar")

    def test_write_read(self):
        from esgf_utilities.esg_env_manager import _EnvWriter
        EnvWriter = _EnvWriter(ENVFILE)
        EnvWriter.export("FOO", "foo")
        self.export_in_second_file()
        EnvWriter.add_source("/a/source/file")

        contents = EnvWriter.read()

        self.assertTrue("export FOO=foo\n" in contents)
        self.assertTrue("export BAR=bar\n" in contents)
        self.assertTrue("source /a/source/file\n" in contents)


if __name__ == '__main__':
    unittest.main()
