import os
import os.path as path

from .methods.command import Command
from .methods.conda import Conda
from .methods.distribution import FileManager
from .methods.easy_install import EasyInstall
from .methods.git import Git
from .methods.package_manager import PackageManager, Pip
from .methods.users_groups import UserMethod, GroupMethod

_FILE_DIR = path.join(path.dirname(__file__), "files")

_BASE = {
    "httpd": {
        "method": PackageManager
    },
    "httpd-start": {
        "method": Command,
        "requires": ["mod-wsgi-install", "esgf-httpd.conf", "esgf-ca-bundle.crt"],
        "command": "service",
        "args": ["httpd", "start"]
    },
    "mod-wsgi": {
        "method": Pip,
        "requires": ["httpd"],
        "version": "4.5.3",
        "pip_name": "${name}==${version}"
    },
    "mod-wsgi-install": {
        "method": Command,
        "requires": ["mod-wsgi"],
        "command": "mod_wsgi-express",
        "args": ["install-module"],
        "check_fn": lambda module: path.isfile(module),
        "check_args": [path.join(os.sep, "etc", "httpd", "modules", "mod_wsgi-py27.so")]
    },
    "esgf-httpd.conf": {
        "method": FileManager,
        "requires": ["httpd"],
        "source": path.join(_FILE_DIR, "httpd", "${name}"),
        "dest": path.join(os.sep, "etc", "httpd", "conf", "httpd.conf")
    },
    "esgf-ca-bundle.crt": {
        "method": FileManager,
        "source": "${ESGF_PARAMS:mirror}/certs/${name}",
        "dest": path.join(os.sep, "etc", "certs", "${name}")
    },
    "postgres": {
        "method": PackageManager,
        "version": "8.4.20",
        "yum": "postgresql-server-${version}"
    },
    "postgres-init": {
        "method": Command,
        "requires": ["postgres"],
        "command": "service",
        "args": ["postgresql", "initdb"],
        "check_fn": lambda datadir: path.isdir(datadir) and bool(os.listdir(datadir)),
        "check_args": [path.join(os.sep, "var", "lib", "pgsql", "data")]
    },
    "postgresql.conf": {
        "method": FileManager,
        "requires": ["postgres-init"],
        "source": path.join(_FILE_DIR, "postgres", "${name}"),
        "dest": path.join(os.sep, "var", "lib", "pgsql", "data", "${name}"),
        "owner_user": "postgres",
        "owner_group": "postgres"
    },
    "pg_hba.conf": {
        "method": FileManager,
        "requires": ["postgres-init"],
        "source": path.join(_FILE_DIR, "postgres", "${name}"),
        "dest": path.join(os.sep, "var", "lib", "pgsql", "data", "${name}"),
        "owner_user": "postgres",
        "owner_group": "postgres"
    },
    "postgres-start": {
        "method": Command,
        "requires": ["pg_hba.conf", "postgresql.conf"],
        "command": "service",
        "args": ["postgresql", "start"]
    },
    "java": {
        "method": FileManager,
        "version": "1.8.0_192",
        "source": "${ESGF_PARAMS:mirror}/java/${version}/jdk${version}-64.tar.gz",
        "dest": os.path.join(os.sep, "usr", "local", "java"),
        "tar_root_dir": "jdk${version}"
    },
    "java-set-default1": {
        "method": Command,
        "requires": ["java"],
        "command": "alternatives",
        "args": ["--install", "${java:dest}", "${java:dest}/bin/java", "3"]
    },
    "java-set-default2": {
        "method": Command,
        "requires": ["java-set-default1"],
        "command": "alternatives",
        "args": ["--set", "java", "${java:dest}/bin/java", "3"]
    },
    "ant": {
        "method": PackageManager
    },
    "postgresql-devel": {
        "method": PackageManager
    },
    "httpd-devel": {
        "method": PackageManager
    },
    "mod_ssl": {
        "method": PackageManager
    },
    # "sqlite-devel": {
    #     "method": PackageManager
    # },
    # "freetype-devel": {
    #     "method": PackageManager
    # },
    # "curl-devel": {
    #     "method": PackageManager
    # },
    # "bison": {
    #     "method": PackageManager
    # },
    # "file": {
    #     "method": PackageManager
    # },
    # "flex": {
    #     "method": PackageManager
    # },
    # "uuid-devel": {
    #     "method": PackageManager
    # },
    # "libtool": {
    #     "method": PackageManager
    # },
    # "gettext-devel": {
    #     "method": PackageManager
    # },
    # "libuuid-devel": {
    #     "method": PackageManager
    # },
    "libxml2": {
        "method": PackageManager
    },
    "libxml2-devel": {
        "method": PackageManager
    },
    "libxslt": {
        "method": PackageManager
    },
    "libxslt-devel": {
        "method": PackageManager
    },
    # "lsof": {
    #     "method": PackageManager
    # },
    # "openssl-devel": {
    #     "method": PackageManager
    # },
    # "pam-devel": {
    #     "method": PackageManager
    # },
    # "pax": {
    #     "method": PackageManager
    # },
    # "tk-devel": {
    #     "method": PackageManager
    # },
    # "zlib-devel": {
    #     "method": PackageManager
    # },
    # "perl-Archive-Tar": {
    #     "method": PackageManager
    # },
    # "perl-XML-Parser": {
    #     "method": PackageManager
    # },
    # "libX11-devel": {
    #     "method": PackageManager
    # },
    # "libtool-ltdl-devel": {
    #     "method": PackageManager
    # },
    # "e2fsprogs-devel": {
    #     "method": PackageManager
    # },
    # "gcc-gfortran": {
    #     "method": PackageManager
    # },
    # "libicu-devel": {
    #     "method": PackageManager
    # },
    # "libgtextutils-devel": {
    #     "method": PackageManager
    # },
    # "libjpeg-turbo-devel": {
    #     "method": PackageManager
    # },
    # "*ExtUtils*": {
    #     "method": PackageManager
    # },
    # "readline-devel": {
    #     "method": PackageManager
    # },
    "tomcat-group": {
        "method": GroupMethod,
        "groupname": "tomcat"
    },
    "tomcat-user": {
        "method": UserMethod,
        "requires": ["tomcat-group"],
        "options": ["-s", "/sbin/nologin", "-g", "${tomcat-group:groupname}", "-d", "/usr/local/tomcat"],
        "username": "tomcat"
    },
    "tomcat": {
        "method": FileManager,
        "requires": ["tomcat-user", "tomcat-group"],
        "version": "8.5.20",
        "source": "http://archive.apache.org/dist/tomcat/tomcat-8/v${version}/bin/apache-tomcat-${version}.tar.gz",
        "dest": path.join(os.sep, "usr", "local", "tomcat"),
        "tar_root_dir": "apache-tomcat-${version}",
        "owner_user": "${tomcat-user:username}",
        "owner_group": "${tomcat-group:groupname}"
    },
    "default-webapp-cleanup": {
        "method": Command,
        "requires": ["tomcat"],
        "command": "rm",
        "args": [
            "-rf",
            path.join("${tomcat:dest}", "webapps", "ROOT"),
            path.join("${tomcat:dest}", "webapps", "docs"),
            path.join("${tomcat:dest}", "webapps", "examples"),
            path.join("${tomcat:dest}", "webapps", "host-manager"),
            path.join("${tomcat:dest}", "webapps", "manager")
        ]
    },
    "tomcat-context.xml": {
        "method": FileManager,
        "requires": ["tomcat"],
        "source": path.join(_FILE_DIR, "tomcat", "context.xml"),
        "dest": path.join("${tomcat:dest}", "conf", "context.xml")
    },
    "tomcat-users.xml": {
        "method": FileManager,
        "requires": ["tomcat"],
        "source": path.join(_FILE_DIR, "tomcat", "tomcat-users.xml"),
        "dest": path.join("${ESGF_PARAMS:config}", "tomcat", "tomcat-users.xml"),
        "owner_user": "${tomcat-user:username}",
        "owner_group": "${tomcat-group:groupname}"
    },
    "tomcat-setenv.sh": {
        "method": FileManager,
        "requires": ["tomcat"],
        "source": path.join(_FILE_DIR, "tomcat", "setenv.sh"),
        "dest": path.join("${tomcat:dest}", "bin", "setenv.sh"),
        "template": True
    }
    # "esgf-config-git": {
    #     "method": Git,
    #     "source": "https://github.com/ESGF/esgf-config.git",
    #     "dest": "/tmp/esgf-config"
    # }
}
_DATA = {
    "thredds": {
        "method": FileManager,
        "requires": ["tomcat"],
        "version": "5.0.2",
        "source": "${ESGF_PARAMS:mirror}/2.6/8/thredds/5.0/${version}/thredds.war",
        "dest": path.join("${tomcat:dest}", "webapps", "thredds")
    },
    "esgf-dashboard-git": {
        "method": Git,
        "tag": "v1.5.20",
        "source": "https://github.com/ESGF/esgf-dashboard.git",
        "dest": "/tmp/esgf-dashboard"
    },
    "cdutil": {
        "method": Conda,
        "channels": ["conda-forge"]
    },
    "cmor": {
        "method": Conda,
        "channels": ["conda-forge"]
    },
    "esgcet": {
        "method": Pip,
        "requires": ["postgres", "postgresql-devel", "libxslt-devel", "libxml2-devel"],
        "version": "3.5.0",
        "tag": "v${version}",
        "repo": "https://github.com/ESGF/esg-publisher.git",
        "egg": "${name}",
        "subdirectory": "src/python/esgcet",
        "pip_name": "git+${repo}@${tag}#egg=${egg}&subdirectory=${subdirectory}"
    },
    "esgf-dashboard": {
        "method": EasyInstall,
        "version": "0.0.2",
        "source": "${ESGF_PARAMS:mirror}/2.6/8/esgf-dashboard/esgf_dashboard-${version}-py2.7.egg",
        "dest": "/tmp/esgf_dashboard/esgf_dashboard.egg",
        "extract": False
    },
    "esgf-node-manager": {
        "method": EasyInstall,
        "version": "0.1.5",
        "source": "${ESGF_PARAMS:mirror}/2.6/8/esgf-node-manager/esgf_node_manager-${version}-py2.7.egg",
        "dest": "/tmp/esgf_node_manager/esgf_node_manager.egg",
        "extract": False
    }
}
_INDEX = {
    "cog": {
        "method": Git,
        "requires": ["httpd"],
        "source": "https://github.com/William-Hill/COG.git",
        "dest": path.join(os.sep, "usr", "local", "cog", "cog-install"),
        "tag": "ESGF_3.0",
        "owner_user": "apache",
        "owner_group": "apache"
    },
    "cog-requirements": {
        "method": Command,
        "requires": ["cog"],
        "command": "pip",
        "args": ["-r", "requirements.txt"],
        "working_dir": "${cog:dest}"
    },
    "cog-setup-install": {
        "method": Command,
        "requires": ["cog-requirements", "postgres-start"],
        "command": "python",
        "args": ["setup.py", "install"],
        "working_dir": "${cog:dest}"
    },
    "cog-setup-setup": {
        "method": Command,
        "requires": ["cog-setup-install"],
        "command": "python",
        "args": ["setup.py", "setup_cog", "--esgf=true"],
        "working_dir": "${cog:dest}"
    },
    "cog-setup-manage": {
        "method": Command,
        "requires": ["cog-setup-setup"],
        "command": "python",
        "args": ["manage.py", "collectstatic", "--no-input"],
        "working_dir": "${cog:dest}"
    },
    "transfer_api_client_python": {
        "method": Git,
        "requires": ["cog-requirements"],
        "source": "https://github.com/globusonline/transfer-api-client-python.git",
        "dest": path.join(os.sep, "usr", "local", "cog", "transfer-api-client-python")
    },
    "make_transfer_api_client": {
        "method": Command,
        "requires": ["transfer_api_client_python"],
        "command": "make",
        "working_dir": path.join("${transfer_api_client_python:dest}", "mkproxy")
    },
    "install_transfer_api_client": {
        "method": Command,
        "requires": ["make_transfer_api_client"],
        "command": "make",
        "args": ["install"],
        "working_dir": "${make_transfer_api_client:working_dir}"
    },
    "django-openid-auth": {
        "method": Pip,
        "repo": "https://github.com/EarthSystemCoG/django-openid-auth.git",
        "egg": "${name}",
        "pip_name": "git+${repo}#egg=${egg}"
    }
}
_TEST = {
    "plumbum": {
        "method": Pip,
        "conda_env": "test-env"
    },
    "pyopenssl": {
        "method": Conda,
        "conda_env": "test-env",
    },
    "echo-env-command": {
        "method": Command,
        "command": "echo",
        "args": ["My conda environment: ${conda_env} $$CONDA_PREFIX"], #Double dollar sign to escape dollar sign, will resolve to a single dollar sign
        "conda_env": "test-env"
    },
    "sample_template": {
        "method": FileManager,
        "source": path.join(_FILE_DIR, "test", "sample.tmpl"),
        "dest": "/tmp/sample.txt",
        "template": True
    },
    "sample_template2": {
        "method": FileManager,
        "source": path.join(_FILE_DIR, "test", "sample.tmpl"),
        "dest": "/tmp/sample2.txt",
        "template": True
    },
    "sample_echo_command": {
        "method": Command,
        "command": "echo",
        "args": ["Fill this value ${ESGF_PARAMS:mirror}", "Filling values in lists ${ESGF_PARAMS:mirror}"]
    },
    "sample_failed_command": {
        "method": Command,
        "command": "rm",
        "args": ["/this/path/DNE"],
        "warn_rc": [1]
    },
    "echo_input_param": {
        "method": Command,
        "command": "echo",
        "args": [
            "From input file",
            "'${INPUT_PARAMS:admin.password}'",
            "'${INPUT_PARAMS:sample.param.override}'",
            # "'${INPUT_PARAMS:this.param.DNE}'",
            "'${INPUT_PARAMS:sample.param}'"
        ]
    },
    "sample_py_fn": {
        "method": Command,
        "requires": ["sample_template2"],
        "command": os.remove,
        "args": ["${sample_template2:dest}"]
    }
}
ALL = {
    "base": _BASE,
    "data": _DATA,
    "index": _INDEX,
    "test": _TEST
}

CONTROL = {
    "base": {
        "start": ["postgres-start", "httpd-start"],
        "stop": [],
        "restart": [],
        "status": []
    },
    "data": {
        "start": [],
        "stop": [],
        "restart": [],
        "status": []
    },
    "index": {
        "start": [],
        "stop": [],
        "restart": [],
        "status": []
    },
    "test": {
        "start": [],
        "stop": [],
        "restart": [],
        "status": []
    }
}