import os
import zipfile
import logging
import yaml
import requests
from clint.textui import progress
from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py


with open(os.path.join(os.path.dirname(__file__), os.pardir, 'esg_config.yaml'), 'r') as config_file:
    config = yaml.load(config_file)

def download_esg_search_war(esg_search_war_url):
    print "\n*******************************"
    print "Downloading ESG Search war file"
    print "******************************* \n"

    r = requests.get(esg_search_war_url, stream=True)
    path = '/usr/local/tomcat/webapps/esg-search/esg-search.war'
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length/1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()

def setup_esg_search():
    '''Setting up the ESG Search application'''

    print "\n*******************************"
    print "Setting up ESG Search"
    print "******************************* \n"

    ESGF_REPO = "http://aims1.llnl.gov/esgf"
    esg_bash2py.mkdir_p("/usr/local/tomcat/webapps/esg-search")
    esg_search_war_url = "{ESGF_REPO}/dist/esg-search/esg-search.war".format(ESGF_REPO=ESGF_REPO)
    download_esg_search_war(esg_search_war_url)
    #Extract esg-search war
    with esg_bash2py.pushd("/usr/local/tomcat/webapps/esg-search"):
        with zipfile.ZipFile("/usr/local/tomcat/webapps/esg-search/esg-search.war", 'r') as zf:
            zf.extractall()
        os.remove("esg-search.war")

    TOMCAT_USER_ID = esg_functions.get_tomcat_user_id()
    TOMCAT_GROUP_ID = esg_functions.get_tomcat_group_id()
    esg_functions.change_ownership_recursive("/usr/local/tomcat/webapps/esg-search", TOMCAT_USER_ID, TOMCAT_GROUP_ID)

def main():
    setup_esg_search()

if __name__ == '__main__':
    main()
