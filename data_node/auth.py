'''Installs the authentication webapp'''
import os
import stat
import string
from random import choice
import pwd
import logging
import zipfile
import pip
from git import Repo

from esgf_utilities import esg_functions
from esgf_utilities import pybash
from esgf_utilities.esg_exceptions import SubprocessError

LOGGER = logging.getLogger('esgf_logger.{}'.format(__name__))


AUTH_INSTALL_DIR = '/usr/local/esgf-auth'
ESGF_AUTH_WEBAPP_CONFIG_PATH = '/esg/config/esgf_auth_config.json'
ESGF_OAUTH2_CREDENTIALS_PATH = '/esg/config/.esgf_oauth2.json'
VERSION = '1.0-alpha'
AUTH_SYSTEM_USER = 'apache'


def check_auth_version():
    '''Checks the version of the currently installed auth webapp'''
    auth_path = '/usr/local/esgf-auth/esgf-auth'
    if os.path.islink(auth_path):
        real_path = os.path.realpath(auth_path)
        version_num = os.path.basename(real_path).lstrip('esgf-auth-')
        print('Found existing Auth installation (Auth version {})'
              .format(version_num))
        return version_num
    return None


def clone_crypto_cookie_repo(install_dir):
    '''Clone the crypto-cookie repo from Github'''
    from git import RemoteProgress

    class Progress(RemoteProgress):
        '''Prints progress of cloning from Github'''
        def update(self, op_code, cur_count, max_count=None, message=''):
            if message:
                print 'Downloading: (==== {} ====)\r'.format(message)
                print 'current line: {}'.format(self._cur_line)
    Repo.clone_from(
        'https://github.com/philipkershaw/crypto-cookie.git',
        install_dir, progress=Progress())


def setup_auth_webapp():
    '''Installs the authentication webapp'''
    apache_uid = pwd.getpwnam(AUTH_SYSTEM_USER).pw_uid

    key_chars = string.ascii_letters + string.digits
    esgf_secret_key = ''.join(choice(key_chars) for i in range(28))
    webapp_secret_key = ''.join(choice(key_chars) for i in range(56))

    esgf_auth_webapp_config = (
        '{\n'
        '    "ESGF_HOSTNAME": "{esgf_hostname}",\n'
        '    "ESGF_SECRET_KEY": "{esgf_secret_key}",\n'
        '    "WEBAPP_SECRET_KEY": "{webapp_secret_key}"\n'
        '}\n'
    )

    esgf_hostname = esg_functions.get_esgf_host()
    with open(ESGF_AUTH_WEBAPP_CONFIG_PATH, 'w') as config_file:
        config_file.write(esgf_auth_webapp_config.format(
            esgf_hostname=esgf_hostname,
            esgf_secret_key=esgf_secret_key,
            webapp_secret_key=webapp_secret_key))

    esgf_oauth2_credentials = (
        '{\n'
        '    "ESGF_IDP_HOSTNAME": {\n'
        '        "key": "",\n'
        '        "secret": ""\n'
        '    }\n'
        '}\n'
    )

    if not os.path.exists(ESGF_OAUTH2_CREDENTIALS_PATH):
        with open(ESGF_OAUTH2_CREDENTIALS_PATH, 'w') as credentials_file:
            credentials_file.write(esgf_oauth2_credentials)
    os.chmod(ESGF_OAUTH2_CREDENTIALS_PATH, stat.S_IRUSR | stat.S_IWUSR)
    os.chown(ESGF_OAUTH2_CREDENTIALS_PATH, apache_uid, -1)

    # Create Auth install directory
    pybash.mkdir_p(AUTH_INSTALL_DIR)

    # Install crypto-cookie package
    crypto_cookie_path = os.path.join(AUTH_INSTALL_DIR, 'crypto-cookie')
    clone_crypto_cookie_repo(crypto_cookie_path)
    with pybash.pushd(crypto_cookie_path):
        pip.main(['install', '-e', '.'])

    # Install Auth Webapp
    with pybash.pushd(AUTH_INSTALL_DIR):
        esg_functions.fetch_remote_file(
            'esgf-auth-v{}'.format(VERSION),
            'https://github.com/ESGF/esgf-auth/archive/v{}.zip'
            .format(VERSION))
        with zipfile.ZipFile('v{}.zip'.format(VERSION), 'r') as zip_file:
            zip_file.extractall()
        os.remove('v{}.zip'.format(VERSION))
        if os.path.islink('esgf-auth'):
            os.unlink('esgf-auth')
        os.symlink('esgf-auth-v{}'.format(VERSION), 'esgf-auth')

    with pybash.pushd(os.path.join(AUTH_INSTALL_DIR, 'esgf-auth')):
        with open("requirements.txt", "r") as req_file:
            requirements = req_file.readlines()
        for req in requirements:
            pip.main(["install", req.strip()])

    # Set up the database
    pybash.mkdir_p(os.path.join(AUTH_INSTALL_DIR, 'db'))
    try:
        esg_functions.stream_subprocess_output('manage.py migrate')
        os.chown(os.path.join(AUTH_INSTALL_DIR, 'db'),
                 apache_uid, -1)
        os.chown(os.path.join(AUTH_INSTALL_DIR, 'db', 'db.sqlite3'),
                 apache_uid, -1)
    except SubprocessError as error:
        LOGGER.debug(error[0]['returncode'])
        if error[0]['returncode'] == 9:
            pass
