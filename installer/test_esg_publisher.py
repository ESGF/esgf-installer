import unittest
import esg_publisher
import os
import shutil
import yaml

with open('esg_config.yaml', 'r') as config_file:
    config = yaml.load(config_file)


class test_ESG_publisher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print "\n*******************************"
        print "Setting up ESGF Publisher Test Fixture"
        print "******************************* \n"
        pass

    @classmethod
    def tearDownClass(cls):
        print "\n*******************************"
        print "Tearing down ESGF Publisher Test Fixture"
        print "******************************* \n"
        try:
            shutil.rmtree("/tmp/esg-publisher")
        except OSError, error:
            print "Error deleting /tmp/esg-publisher", error
        pass

    def test_clone_publisher_repo(self):
        esg_publisher.clone_publisher_repo("/tmp/esg-publisher")
        self.assertTrue(os.path.isdir("/tmp/esg-publisher/.git"))

        repo = esg_publisher.checkout_publisher_branch("/tmp/esg-publisher", "v3.2.7")
        branch = repo.active_branch
        print "active branch:", branch.name
        self.assertEquals(branch.name, "v3.2.7")

    # def test_checkout_publisher_branch(self):
    #     repo = checkout_publisher_branch("/tmp/esg-publisher", "v3.2.7")
    #     branch = repo.active_branch
    #     print "active branch:", branch.name
    #     self.assertEquals(branch.name, "v3.2.7")


    # def test_esgcet():
    #     print '''
    #     ----------------------------
    #     ESGCET Test...
    #     ----------------------------
    #     '''
    #     starting_directory = os.getcwd()
    #     os.chdir(config["workdir"])
    #
    #     esg_postgres.start_postgress()
    #
    #     esgcet_testdir = os.path.join(config[
    #                                   "thredds_root_dir"], "test")
    #
    #     try:
    #         os.makedirs(esgcet_testdir)
    #     except OSError, exception:
    #         if exception.errno != 17:
    #             raise
    #         sleep(1)
    #         pass
    #     except Exception, exception:
    #         print "Exception occurred when attempting to create the {esgcet_testdir} directory: {exception}".format(esgcet_testdir=esgcet_testdir, exception=exception)
    #         esg_functions.exit_with_error(1)
    #
    #     os.chown(esgcet_testdir, config[
    #              "installer_uid"], config["installer_gid"])
    #
    #     try:
    #         os.mkdir(config["thredds_replica_dir"])
    #     except OSError, exception:
    #         if exception.errno != 17:
    #             raise
    #         sleep(1)
    #         pass
    #     except Exception, exception:
    #         print "Exception occurred when attempting to create the {esgcet_testdir} directory: {exception}".format(esgcet_testdir=esgcet_testdir, exception=exception)
    #         esg_functions.exit_with_error(1)
    #
    #     os.chown(config["thredds_replica_dir"], config[
    #              "installer_uid"], config["installer_gid"])
    #     print "esgcet test directory: [%s]" % esgcet_testdir
    #
    #     fetch_file = "sftlf.nc"
    #     if esg_functions.checked_get(os.path.join(esgcet_testdir, fetch_file), "http://" + config["esg_dist_url_root"] + "/externals/" + fetch_file) > 0:
    #         print " ERROR: Problem pulling down %s from esg distribution" % (fetch_file)
    #         os.chdir(starting_directory)
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
