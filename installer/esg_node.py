import os
import subprocess
import requests
import pip
import hashlib
import shutil
import grp
import datetime
from git import Repo
from time import sleep
import esg_functions
import esg_bash2py
import esg_functions
from esg_init import EsgInit


config = EsgInit()
# os.environ['DISCOVERONLY'] = Expand.colonMinus("DISCOVERONLY")
os.environ['LANG'] = "POSIX"
os.umask(022)

DEBUG = esg_bash2py.Expand.colonMinus("DEBUG", "0")
VERBOSE = esg_bash2py.Expand.colonMinus("VERBOSE", "0")

devel = esg_bash2py.Expand.colonMinus("devel", "0")
recommended="1"
custom="0"
use_local_files="0"

progname="esg-node"
script_version="v2.0-RC5.4.0-devel"
script_maj_version="2.0"
script_release="Centaur"
envfile="/etc/esg.env"
force_install = False
upgrade_mode = 0
esg_dist_url="http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist"

#--------------
#User Defined / Settable (public)
#--------------
# install_prefix=${install_prefix:-${ESGF_INSTALL_PREFIX:-"/usr/local"}}
install_prefix = esg_bash2py.Expand.colonMinus(config.install_prefix, esg_bash2py.Expand.colonMinus("ESGF_INSTALL_PREFIX", "/usr/local"))
#--------------

# os.environ['UVCDAT_ANONYMOUS_LOG'] = False

esg_root_id = None
try:
    esg_root_id = config.config_dictionary["esg_root_id"]
except KeyError:
    esg_root_id = esg_functions.get_property("esg_root_id")

node_short_name = None
try:
    node_short_name = config.config_dictionary["node_short_name"]
except:
    node_short_name = esg_functions.get_property("node_short_name")
# write_java_env() {
#     ((show_summary_latch++))
#     echo "export JAVA_HOME=${java_install_dir}" >> ${envfile}
#     prefix_to_path PATH ${java_install_dir}/bin >> ${envfile}
#     dedup ${envfile} && source ${envfile}
#     return 0
# }

# def write_java_env():
#   config.config_dictionary["show_summary_latch"]++
#   # target = open(filename, 'w')
#   target = open(config.config_dictionary['envfile'], 'w')
#   target.write("export JAVA_HOME="+config.config_dictionary["java_install_dir"])

'''
    ESGCET Package (Publisher)
'''
def setup_esgcet(upgrade_mode = None):
    print "Checking for esgcet (publisher) %s " % (config.config_dictionary["esgcet_version"])
    #TODO: come up with better name
    publisher_module_check = esg_functions.check_module_version("esgcet", config.config_dictionary["esgcet_version"])


    #TODO: implement this if block
    # if os.path.isfile(config.config_dictionary["ESGINI"]):
    #   urls_mis_match=1
    #   # files= subprocess.Popen('ls -t | grep %s.\*.tgz | tail -n +$((%i+1)) | xargs' %(source_backup_name,int(num_of_backups)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    #   esgini_dburl = files= subprocess.Popen("sed -n 's@^[^#]*[ ]*dburl[ ]*=[ ]*\(.*\)$@\1@p' %s | head -n1 | sed 's@\r@@'' " %(config.config_dictionary["ESGINI"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if publisher_module_check == 0 and not force_install:
        print "[OK]: Publisher already installed"
        return 0

    upgrade = upgrade_mode if upgrade_mode is not None else publisher_module_check
    
    if upgrade == 1 and not force_install:
        mode = "U"
    else:
        mode = "I"


    print '''
        *******************************
        Setting up ESGCET Package...(%s) [%s]
        *******************************
     ''' % (config.config_dictionary["esgcet_egg_file"], mode)

    if mode == "U":
        if config.config_dictionary["publisher_home"] == os.environ["HOME"]+"/.esgcet":
            print "user configuration", config.config_dictionary["publisher_home"]
        else:
            print "system configuration", config.config_dictionary["publisher_home"]

    default_upgrade_answer = None
    if force_install:
        default_upgrade_answer = "N"
    else:
        default_upgrade_answer = "Y"

    continue_installation_answer = None

    if os.path.isfile(os.path.join(config.config_dictionary["publisher_home"],config.config_dictionary["publisher_config"])):
        print "Detected an existing esgcet installation..."
        if default_upgrade_answer == "N":
            continue_installation_answer = raw_input("Do you want to continue with esgcet installation and setup? [y/N]")
        else:
            continue_installation_answer = raw_input("Do you want to continue with esgcet installation and setup? [Y/n]")
        if not continue_installation_answer.strip():
            continue_installation_answer = default_upgrade_answer

        if continue_installation_answer.lower() != "y":
            print "Skipping esgcet installation and setup - will assume esgcet is setup properly"
            return 0

    try:
        os.mkdir(config.config_dictionary["workdir"])
    except OSError, e:
        if e.errno != 17:
            raise
        sleep(1)
        pass

    print "current directory: ", os.getcwd()
    starting_directory = os.getcwd()
    '''
        curl -s -L --insecure $esg_dist_url/externals/piplist.txt|while read ln; do
          echo "wget $esg_dist_url/externals/$ln" && wget --no-check-certificate $esg_dist_url/externals/$ln
          diff <(md5sum ${ln} | tr -s " " | cut -d " " -f 1) <(curl -s -L --insecure $esg_dist_url/externals/${ln}.md5 | tr -s " " | cut -d " " -f 1) >& /dev/null
          if [ $? -eq 0 ]; then
             [OK]
             echo "${cdat_home}/bin/pip install $ln" && ${cdat_home}/bin/pip install $ln
          else
             [FAIL]
          fi
        done
    '''

    '''
        source ${cdat_home}/bin/activate esgf-pub
        conda install -c conda-forge lxml requests psycopg2 decorator Tempita myproxyclient
        
        if [ $ESGF_INSECURE > 0 ] ; then

        pipcmd="pip install  --index-url=http://pypi.python.org/simple --trusted-host pypi.python.org"
        else
        pipcmd="pip install"
        fi
        
        $pipcmd esgprep
        $pipcmd SQLAlchemy==0.7.10
        $pipcmd sqlalchemy_migrate
    '''
    '''
        lxml-3.3.5.tar.gz
requests-1.2.3.tar.gz
SQLAlchemy-0.7.10.tar.gz
sqlalchemy-migrate-0.6.tar.gz
psycopg2-2.5.tar.gz
Tempita-0.5.1.tar.gz
decorator-3.4.0.tar.gz
pysolr-3.3.0.tar.gz
drslib-0.3.1p3.tar.gz
    '''
    pip_list = [{"package": "lxml", "version": "3.3.5"}, {"package": "requests", "version": "1.2.3"}, {"package": "SQLAlchemy", "version": "0.7.10"}, 
    {"package": "sqlalchemy-migrate", "version":"0.6" },{"package":"psycopg2", "version":"2.5"}, {"package": "Tempita", "version":"0.5.1"}, 
    {"package": "decorator", "version":"3.4.0"}, {"package": "pysolr", "version": "3.3.0"}, {"package": "drslib", "version": "0.3.1p3"} ]

    for i,value in enumerate(pip_list):
     # print "i:", i     
     # print "package:", value["package"]     
     # print "version:", value["version"]
     print "installing %s-%s" % (value["package"], value["version"])
     pip.main(["install", value["package"]+ "=="+ value["version"]])
    # r = requests.get(esg_dist_url+"/externals/piplist.txt")
    # print "r.text: ", r.text
    # pip_package_list_names = str(r.text).split()
    # for name in pip_package_list_names:
    #     print "downloading %s: " % (name)
    #     r = requests.get(esg_dist_url+"/externals/"+name)
    #     if r.status_code == requests.codes.ok:
    #         hasher = hashlib.md5()
    #         with open(r, 'rb') as f:
    #             buf = f.read()
    #             hasher.update(buf)
    #             pip_download_md5 = hasher.hexdigest()
    #             print "pip_download_md5 in checked_get: ", pip_download_md5


    #     pip_package_remote_md5 = requests.get(esg_dist_url+"/externals/"+name+".md5").content
    #     pip_package_remote_md5 = pip_package_remote_md5.split()[0].strip()
    #     if pip_download_md5 != pip_package_remote_md5:
    #         print " WARNING: Could not verify this file!"
    #         print "[FAIL]"
    #     else:
    #         print "[OK]"
    #         pip.main(['install', name])
    #clone publisher
    publisher_git_protocol="git://"

    if force_install and os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher"):
        try:
            shutil.rmtree(config.config_dictionary["workdir"]+"esg-publisher")
        except:
            print "Could not delete directory: %s" % (config.config_dictionary["workdir"]+"esg-publisher")

    if os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher"):
        print "Fetching the cdat project from GIT Repo... %s" % (config.config_dictionary["publisher_repo"])
        Repo.clone_from(config.config_dictionary["publisher_repo"], config.config_dictionary["workdir"]+"esg-publisher")
        if not os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher/.git"):
            publisher_git_protocol="https://"
            print "Apparently was not able to fetch from GIT repo using git protocol... trying https protocol... %s" % (publisher_git_protocol)
            Repo.clone_from(config.config_dictionary["publisher_repo_https"], os.path.join(config.config_dictionary["workdir"],"esg-publisher"))
            if not os.path.isdir(config.config_dictionary["workdir"]+"esg-publisher/.git"):
                print "Could not fetch from cdat's repo (with git nor https protocol)"
                esg_functions.checked_done(1)

    os.chdir(os.path.join(config.config_dictionary["workdir"],"esg-publisher"))
    publisher_repo_local = Repo(os.path.join(config.config_dictionary["workdir"],"esg-publisher"))
    #pull from remote
    publisher_repo_local.remotes.origin.pull()
    #Checkout publisher tag
    try:
        publisher_repo_local.head.reference = publisher_repo_local.tags[config.config_dictionary["publisher_tag"]]
        publisher_repo_local.head.reset(index=True, working_tree=True)
    except:
        print " WARNING: Problem with checking out publisher (esgcet) revision [%s] from repository :-(" % (config.config_dictionary["esgcet_version"])

    #install publisher
    '''
    output = subprocess.check_output(
    'echo to stdout; echo to stderr 1>&2; exit 1',
    shell=True,
    )
    '''
    installation_command = "cd src/python/esgcet; %s/bin/python setup.py install" % (config.config_dictionary["cdat_home"])
    try:
        output = subprocess.call(installation_command, shell=True)
        if output != 0:
            esg_functions.checked_done(1)
    except:
        esg_functions.checked_done(1)

    if mode == "I":
        choice = None

        while choice != 0:
            print "Would you like a \"system\" or \"user\" publisher configuration: \n"
            print "\t-------------------------------------------\n"
            print "\t*[1] : System\n"
            print "\t [2] : User\n"
            print "\t-------------------------------------------\n"
            print "\t [C] : (Custom)\n"
            print "\t-------------------------------------------\n"

            choice = raw_input("select [1] > ")
            if choice == 1:
                config.config_dictionary["publisher_home"]=config.esg_config_dir+"/esgcet"
            elif choice == 2:
                config.config_dictionary["publisher_home"]=os.environ["HOME"]+"/.esgcet"
            elif choice.lower() == "c":
                # input = None
                publisher_config_directory_input = raw_input("Please enter the desired publisher configuration directory [%s] " %  config.config_dictionary["publisher_home"])
                config.config_dictionary["publisher_home"] = publisher_config_directory_input
                publisher_config_filename_input = raw_input("Please enter the desired publisher configuration filename [%s] " % config.config_dictionary["publisher_config"])
                choice = "(Manual Entry)"
            else:
                print "Invalid Selection %s " % (choice)

            print "You have selected: %s" % (choice)
            print "Publisher configuration file -> [%s/%s]" % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])
            is_correct = raw_input("Is this correct? [Y/n] ")
            if is_correct.lower() == "n":
                continue
            else:
                break


        config.config_dictionary["ESGINI"] =  os.path.join(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])
        print "Publisher configuration file -> [%s/%s]" % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"])

        esgf_host = None
        try:
            esgf_host = config.config_dictionary["esgf_host"]
        except KeyError:
            esgf_host = esg_functions.get_property("esgf_host")

        org_id_input = raw_input("What is your organization's id? [%s]: " % esg_root_id)
        if org_id_input:
            esg_root_id = org_id_input


        print "%s/bin/esgsetup --config $( ((%s == 1 )) && echo '--minimal-setup' ) --rootid %s" % (config.config_dictionary["cdat_home"], recommended, esg_root_id)
        os.mkdir(config.config_dictionary["publisher_home"])
        ESGINI = subprocess.Popen('''
            %s/%s $cdat_home/bin/esgsetup --config $( ((%s == 1 )) && echo "--minimal-setup" ) --rootid %s
            sed -i s/"host\.sample\.gov"/%s/g %s/%s 
            sed -i s/"LASatYourHost"/LASat%s/g %s/%s 
            ''' % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"], recommended, esg_root_id, esgf_host,config.config_dictionary["publisher_home"],config.config_dictionary["publisher_config"],node_short_name, config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"]), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        if ESGINI.returncode != 0:
            os.chdir(starting_directory)
            esg_functions.checked_done(1)

    print "chown -R %s:%s %s" % (config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"], config.config_dictionary["publisher_home"])
    try:
        os.chown(config.config_dictionary["publisher_home"], config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"])
    except:
        print "**WARNING**: Could not change owner successfully - this will lead to inability to use the publisher properly!"

    #Let's make sure the group is there before we attempt to assign a file to it....
    try:
        tomcat_group_check = grp.getgrnam(config.config_dictionary["tomcat_group"])
    except KeyError:
        groupadd_command = "/usr/sbin/groupadd -r %s" % (config.config_dictionary["tomcat_group"])
        groupadd_output = subprocess.call(groupadd_command, shell=True)
        if groupadd_output !=0 or groupadd_output !=9:
            print "ERROR: *Could not add tomcat system group: %s" % (config.config_dictionary["tomcat_group"])
            os.chdir(starting_directory)
            esg_functions.checked_done(1)
    
    try:
        tomcat_group_id = grp.getgrnam(config.config_dictionary["tomcat_group"]).gr_gid
        os.chown(os.path.join(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"]), -1, tomcat_group_id)
        os.chmod(os.path.join(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"]), 0640)
    except:
        print "**WARNING**: Could not change group successfully - this will lead to inability to use the publisher properly!"

    start_postgress()

    # security_admin_password=$(cat ${esgf_secret_file} 2> /dev/null)
    security_admin_password = None
    with open(config.esgf_secret_file, 'rb') as f:
        security_admin_password = f.read()

    # get_property publisher_db_user ${publisher_db_user}
    publisher_db_user = None
    if config.config_dictionary["publisher_db_user"]:
        publisher_db_user = config.config_dictionary["publisher_db_user"]
    else:
        publisher_db_user = esg_functions.get_property("publisher_db_user")

    if mode == "I":
        if DEBUG != "0":
           print  '''ESGINI = 
                    %s/%s $cdat_home/bin/esgsetup $( ((%s == 1 )) && echo "--minimal-setup" ) 
                    --db $( [ -n "%s" ] && echo "--db-name %s" ) $( [ -n "%s" ] 
                    && echo "--db-admin %s" ) $([ -n "${pg_sys_acct_passwd:=%s}" ] 
                    && echo "--db-admin-password %s") 
                    $( [ -n "%s" ] && echo "--db-user %s" ) 
                    $([ -n "%s" ] && echo "--db-user-password %s") 
                    $( [ -n "%s" ] && echo "--db-host %s" ) 
                    $( [ -n "%s" ] && echo "--db-port %s" )" % 
            ''' % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"], recommended, config.config_dictionary["db_database"], 
                config.config_dictionary["postgress_user"], config.config_dictionary["postgress_user"], security_admin_password, config.config_dictionary["pg_sys_acct_passwd"],
                publisher_db_user, publisher_db_user, config.config_dictionary["publisher_db_user_passwd"], config.config_dictionary["publisher_db_user_passwd"], 
                config.config_dictionary["postgress_host"], config.config_dictionary["postgress_host"], config.config_dictionary["postgress_port"], config.config_dictionary["postgress_port"] )

        else:
           print ''' ESGINI = 
                    %s/%s $cdat_home/bin/esgsetup $( ((%s == 1 )) && echo "--minimal-setup" ) 
                    --db $( [ -n "%s" ] && echo "--db-name %s" ) $( [ -n "%s" ] 
                    && echo "--db-admin %s" ) $([ -n "${pg_sys_acct_passwd:=%s}" ] 
                    && echo "--db-admin-password %s") 
                    $( [ -n "%s" ] && echo "--db-user %s" ) 
                    $([ -n "%s" ] && echo "--db-user-password %s") 
                    $( [ -n "%s" ] && echo "--db-host %s" ) 
                    $( [ -n "%s" ] && echo "--db-port %s" )" % 
            ''' % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"], recommended, config.config_dictionary["db_database"], 
                config.config_dictionary["postgress_user"], config.config_dictionary["postgress_user"], security_admin_password, "******",
                publisher_db_user, publisher_db_user, "******", config.config_dictionary["publisher_db_user_passwd"], 
                config.config_dictionary["postgress_host"], config.config_dictionary["postgress_host"], config.config_dictionary["postgress_port"], config.config_dictionary["postgress_port"] )

    try:

        ESGINI = '''    %s/%s $cdat_home/bin/esgsetup $( ((%s == 1 )) && echo "--minimal-setup" ) 
                        --db $( [ -n "%s" ] && echo "--db-name %s" ) $( [ -n "%s" ] 
                        && echo "--db-admin %s" ) $([ -n "${pg_sys_acct_passwd:=%s}" ] 
                        && echo "--db-admin-password %s") 
                        $( [ -n "%s" ] && echo "--db-user %s" ) 
                        $([ -n "%s" ] && echo "--db-user-password %s") 
                        $( [ -n "%s" ] && echo "--db-host %s" ) 
                        $( [ -n "%s" ] && echo "--db-port %s" )" % 
                ''' % (config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"], recommended, config.config_dictionary["db_database"], 
                    config.config_dictionary["postgress_user"], config.config_dictionary["postgress_user"], security_admin_password, config.config_dictionary["pg_sys_acct_passwd"],
                    publisher_db_user, publisher_db_user, config.config_dictionary["publisher_db_user_passwd"], config.config_dictionary["publisher_db_user_passwd"], 
                    config.config_dictionary["postgress_host"], config.config_dictionary["postgress_host"], config.config_dictionary["postgress_port"], config.config_dictionary["postgress_port"] )
    except:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)



    esginitialize_output = subprocess.call("%s/bin/esginitialize -c" % (config.config_dictionary["cdat_home"]))
    if esginitialize_output != 0:
        os.chdir(starting_directory)
        esg_functions.checked_done(1)


    os.chdir(starting_directory)
    write_esgcet_env()
    write_esgcet_install_log()

    esg_functions.checked_done(0)


def write_esgcet_env():
    # print
    datafile = open(config.envfile, "a+")
    datafile.write("export ESG_ROOT_ID="+config.config_dictionary["esg_root_id"])
    esg_functions.deduplicate(config.envfile)
    datafile.close()

def write_esgcet_install_log():
    datafile = open(config.install_manifest, "a+")
    datafile.write(str(datetime.date.today()) + "python:esgcet=" + config.config_dictionary["esgcet_version"])
    esg_functions.deduplicate(config.install_manifest)
    datafile.close()
    esg_functions.write_as_property("publisher_config", config.config_dictionary["publisher_config"])
    esg_functions.write_as_property("publisher_home", config.config_dictionary["publisher_home"])
    esg_functions.write_as_property("monitor.esg.ini", os.path.join(config.config_dictionary["publisher_home"], config.config_dictionary["publisher_config"]))
    return 0

def test_esgcet():
	print '''
    	"----------------------------"
    	"ESGCET Test... "
    	"----------------------------"
    '''
	starting_directory = os.getcwd()
	os.chdir(config.config_dictionary["workdir"])

	start_postgress()

	esgcet_testdir=os.path.join(config.config_dictionary["thredds_root_dir"], "test")
	try:
		os.mkdir(esgcet_testdir)
	except:
		esg_functions.checked_done(1)

	os.chown(esgcet_testdir, config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"])

	try:
		os.mkdir(config.config_dictionary["thredds_replica_dir"])
	except:
		esg_functions.checked_done(1)

	os.chown(config.config_dictionary["thredds_replica_dir"], config.config_dictionary["installer_uid"], config.config_dictionary["installer_gid"])
	print "esgcet test directory: [%s]" % esgcet_testdir

	fetch_file="sftlf.nc"
	if esg_functions.checked_get(os.path.join(esgcet_testdir,fetch_file), config.config_dictionary["esg_dist_url_root"]+"/externals/"+fetch_file) > 0:
		print " ERROR: Problem pulling down %s from esg distribution" % (fetch_file)
		os.chdir(starting_directory)
		esg_functions.checked_done(1)

	#Run test...
	print "%s/bin/esginitialize -c " % (config.config_dictionary["cdat_home"])
	esginitialize_output = subprocess.call("%s/bin/esginitialize -c" % (config.config_dictionary["cdat_home"]))
	print '''
		%s/bin/esgscan_directory --dataset pcmdi.%s.%s.
		test.mytest --project test %s > mytest.txt
		''' % (config.config_dictionary["cdat_home"], esg_root_id, node_short_name, esgcet_testdir)
	esgscan_directory_output = subprocess.call('''
		%s/bin/esgscan_directory --dataset pcmdi.%s.%s.
		test.mytest --project test %s > mytest.txt
		''' % (config.config_dictionary["cdat_home"], esg_root_id, node_short_name, esgcet_testdir))
	if esgscan_directory_output !=0:
		print " ERROR: ESG directory scan failed"
		os.chdir(starting_directory)
		esg_functions.checked_done(1) 

	print "$cdat_home/bin/esgpublish --service fileservice --map mytest.txt --project test --model test" % (config.config_dictionary["cdat_home"])
	esgpublish_output = subprocess.call("$cdat_home/bin/esgpublish --service fileservice --map mytest.txt --project test --model test" % (config.config_dictionary["cdat_home"]))
	if esgpublish_output != 0:
		print " ERROR: ESG publish failed"
		os.chdir(starting_directory)
		esg_functions.checked_done(1)

	os.chdir(starting_directory)
	esg_functions.checked_done(0) 

	pass

#returns 1 if it is already running (if check_postgress_process returns 0 - true)
def start_postgress():
    if esg_functions.check_postgress_process() == 0:
        print "Postgres is already running"
        return 1
    print "Starting Postgress..."
    status = subprocess.check_output(["/etc/init.d/postgresql", "start"])
    sleep(3)
    progress_process_status = subprocess.Popen("/bin/ps -elf | grep postgres | grep -v grep")
    progress_process_status_tuple = progress_process_status.communicate()
    esg_functions.checked_done(0)

def main():

    print "inside main function of esg_node"
    setup_esgcet()
    # internal_node_code_versions = {}
    # test = EsgInit()
    # print "install_prefix: ", test.install_prefix

    # internal_node_code_versions = test.populate_internal_esgf_node_code_versions()
    # print internal_node_code_versions
    # print "apache_frontend_version: ", internal_node_code_versions["apache_frontend_version"]   

    # local_test = test.populate_external_programs_versions()
    # print "local_test: ", local_test
    # print "globals type: ", type(globals())
    # globals().update(local_test)
    # print "globals: ", globals()

    # ext_script_vars = test.populate_external_script_variables()
    # globals().update(ext_script_vars)
    # print "globals after update: ", globals()


if __name__ == '__main__':
    main()