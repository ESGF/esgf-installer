import unittest
import esg_publisher
import esg_postgres
import esg_bash2py
import os
import shutil
import yaml

with open(os.path.join(os.path.dirname(__file__), 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_publisher(unittest.TestCase):

    def purge_publisher(self):
        try:
            shutil.rmtree("/tmp/esg-publisher")
        except OSError, error:
            print "Could not purge esg-publisher", error

    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Publisher Test Fixture"
        print "******************************* \n"
        esg_postgres.setup_postgres()

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Tearing down ESGF Publisher Test Fixture"
        print "******************************* \n"
        try:
            shutil.rmtree("/tmp/esg-publisher")
        except OSError, error:
            print "Error deleting /tmp/esg-publisher", error

        try:
            shutil.rmtree("/esg/config/esgcet")
        except OSError, error:
            print "Error deleting /esg/config/esgcet", error

    def test_clone_publisher_repo(self):
        esg_publisher.clone_publisher_repo("/tmp/esg-publisher")
        self.assertTrue(os.path.isdir("/tmp/esg-publisher/.git"))

        repo = esg_publisher.checkout_publisher_branch("/tmp/esg-publisher", "devel")
        branch = repo.active_branch
        print "active branch:", branch.name
        self.assertEquals(branch.name, "devel")

        self.purge_publisher()

    def test_setup_publisher(self):
        esg_publisher.setup_publisher()
        self.assertTrue(os.path.isdir('/usr/local/conda/envs/esgf-pub/lib/python2.7/site-packages/esgcet-3.2.8-py2.7.egg'))

        output = esg_publisher.check_publisher_version()
        self.assertEqual(output, "3.2.8")

        esg_bash2py.mkdir_p("/esg/config/esgcet")
        os.environ["UVCDAT_ANONYMOUS_LOG"] = "no"
        esg_publisher.run_esgsetup()
        self.assertTrue(os.path.isfile("/esg/config/esgcet/esg.ini"))

        esg_publisher.run_esginitialize()
        self.assertTrue(os.path.isdir("/esg/data"))

    def test_generate_esgsetup_options(self):
        output = esg_publisher.generate_esgsetup_options()
        print "output:", output
        self.assertTrue(output)

    # def test_checkout_publisher_branch(self):
    #     repo = checkout_publisher_branch("/tmp/esg-publisher", "v3.2.7")
    #     branch = repo.active_branch
    #     print "active branch:", branch.name
    #     self.assertEquals(branch.name, "v3.2.7")

    # def test_run_esgsetup(self):
    #     esg_publisher.run_esgsetup()
    #     self.assertTrue(os.path.isfile("/esg/config/esgcet/esg.ini"))



    # def test_esgcet(self):
    #     print "\n*******************************"
    #     print "Publisher Test"
    #     print "******************************* \n"
    #     starting_directory = os.getcwd()
    #     os.chdir(config["workdir"])
    #
    #     esg_postgres.start_postgres()
    #
    #     esgcet_testdir = os.path.join(config[
    #                                   "thredds_root_dir"], "test")
    #     esg_bash2py.mkdir_p(esgcet_testdir)
    #
    #     os.chown(esgcet_testdir, config[
    #              "installer_uid"], config["installer_gid"])
    #
    #     esg_bash2py.mkdir_p(config["thredds_replica_dir"])
    #
    #     os.chown(config["thredds_replica_dir"], config[
    #              "installer_uid"], config["installer_gid"])
    #     print "esgcet test directory: [%s]" % esgcet_testdir
    #
    #     fetch_file = "sftlf.nc"
    #     if not esg_functions.download_update(os.path.join(esgcet_testdir, fetch_file), "http://" + config["esg_dist_url_root"] + "/externals/" + fetch_file):
    #         print " ERROR: Problem pulling down %s from esg distribution" % (fetch_file)
    #         esg_functions.exit_with_error(1)
    #
    #     # Run test...
    #     print "%s/bin/esginitialize -c " % (config["cdat_home"])
    #     esginitialize_output = subprocess.call(
    #         "%s/bin/esginitialize -c" % (config["cdat_home"]), shell=True)
    #
    #     print '''
    #         {cdat_home}/bin/esgprep mapfile --dataset ipsl.fr.test.mytest --project test {esgcet_testdir}; mv ipsl.fr.test.mytest.map test_mapfile.txt
    #         '''.format(cdat_home=config["cdat_home"], esg_root_id=esg_root_id, node_short_name=node_short_name, esgcet_testdir=esgcet_testdir)
    #     esgprep_output = subprocess.call('''
    #         {cdat_home}/bin/esgprep mapfile --dataset ipsl.fr.test.mytest --project test {esgcet_testdir}; mv ipsl.fr.test.mytest.map test_mapfile.txt
    #         '''.format(cdat_home=config["cdat_home"], esg_root_id=esg_root_id, node_short_name=node_short_name, esgcet_testdir=esgcet_testdir), shell=True)
    #     if esgprep_output != 0:
    #         print " ERROR: ESG Mapfile generation failed"
    #         os.chdir(starting_directory)
    #         esg_functions.exit_with_error(1)
    #
    #     print "{cdat_home}/bin/esgpublish --service fileservice --map test_mapfile.txt --project test --thredds".format(cdat_home=config["cdat_home"])
    #     esgpublish_output = subprocess.call("{cdat_home}/bin/esgpublish --service fileservice --map test_mapfile.txt --project test --thredds".format(
    #         cdat_home=config["cdat_home"]), shell=True)
    #     if esgpublish_output != 0:
    #         print " ERROR: ESG publish failed"
    #         os.chdir(starting_directory)
    #         esg_functions.exit_with_error(1)
    #
    #     os.chdir(starting_directory)
    #     esg_functions.exit_with_error(0)

if __name__ == '__main__':
    unittest.main()
