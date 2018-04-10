import os
import stat
import string
from random import choice
import pwd
import logging
import zipfile
import pip
from git import Repo, GitCommandError

from esgf_utilities import esg_functions
from esgf_utilities import esg_bash2py
from esgf_utilities import esg_property_manager
from esgf_utilities.esg_exceptions import SubprocessError

logger = logging.getLogger('esgf_logger.{}'.format(__name__))


auth_install_dir = '/usr/local/esgf-auth'
esgf_auth_webapp_config_path = '/esg/config/esgf_auth_config.json'
esgf_oauth2_credentials_path = '/esg/config/.esgf_oauth2.json'
version = '1.0-alpha'
auth_system_user = 'apache'


def check_auth_version():
    auth_path = '/usr/local/esgf-auth/esgf-auth'
    if os.path.islink(auth_path):
        real_path = os.path.realpath(auth_path)
        version = os.path.basename(real_path).lstrip('esgf-auth-')
        print('Found existing Auth installation (Auth version {})'
              .format(version))
        return version
    return None


def clone_crypto_cookie_repo(install_dir, tag):

    from git import RemoteProgress

    class Progress(RemoteProgress):
        def update(self, op_code, cur_count, max_count=None, message=''):
            if message:
                print('Downloading: (==== {} ====)\r'.format(message))
                print('current line: {}'.format(self._cur_line))
    Repo.clone_from(
            'https://github.com/philipkershaw/crypto-cookie.git',
            install_dir, progress=Progress())


def setup_auth_webapp(auth_dir='/usr/local/esgf-auth'):

    apache_uid = pwd.getpwnam(auth_system_user).pw_uid

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
    with open(esgf_auth_webapp_config_path, 'w') as f:
        f.write(esgf_auth_webapp_config.format(
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

    if not os.path.exists(esgf_oauth2_credentials_path):
        with open(esgf_oauth2_credentials_path, 'w') as f:
            f.write(esgf_oauth2_credentials)
    os.chmod(esgf_oauth2_credentials_path, stat.S_IRUSR | stat.S_IWUSR)
    os.chown(esgf_oauth2_credentials_path, apache_uid, -1)

    # Create Auth install directory
    esg_bash2py.mkdir_p(auth_install_dir)

    # Install crypto-cookie package
    crypto_cookie_path = os.path.join(auth_install_dir, 'crypto-cookie')
    clone_crypto_cookie_repo(crypto_cookie_path, None)
    with esg_bash2py.pushd(crypto_cookie_path):
        pip.main(['install', '-e', '.'])

    # Install Auth Webapp
    with esg_bash2py.pushd(auth_install_dir):
        esg_functions.fetch_remote_file(
                'esgf-auth-v{}'.format(version),
                'https://github.com/ESGF/esgf-auth/archive/v{}.zip'
                .format(version))
        with zipfile.ZipFile('v{}.zip'.format(version), 'r') as zf:
            zf.extractall()
        os.remove('v{}.zip'.format(version))
        if os.path.islink('esgf-auth'):
            os.unlink('esgf-auth')
        os.symlink('esgf-auth-v{}'.format(version), 'esgf-auth')

    with esg_bash2py.pushd(os.path.join(auth_install_dir, 'esgf-auth')):
        with open("requirements.txt", "r") as req_file:
            requirements = req_file.readlines()
        for req in requirements:
            pip.main(["install", req.strip()])

    # Set up the database
    esg_bash2py.mkdir_p(os.path.join(auth_install_dir, 'db'))
    try:
        esg_functions.stream_subprocess_output('manage.py migrate')
        os.chown(os.path.join(auth_install_dir, 'db'),
                 apache_uid, -1)
        os.chown(os.path.join(auth_install_dir, 'db', 'db.sqlite3'),
                 apache_uid, -1)
    except SubprocessError as error:
        logger.debug(error[0]['returncode'])
        if error[0]['returncode'] == 9:
            pass
