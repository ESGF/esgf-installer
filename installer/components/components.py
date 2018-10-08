import os
import os.path as path

import base
import data
from .files import FileComponent
from .syspkg import SysPkgComponent
from .pip import PipComponent
from .conda import CondaComponent
from .make import MakeComponent
from .command import CommandComponent
from .users_groups import UserComponent, GroupComponent
from ..methods.distribution import FileManager
from ..methods.git import Git
from ..methods.command import Command
from ..methods.conda import Conda
from ..methods.package_manager import PackageManager, Pip
from ..methods.easy_install import EasyInstall
from ..methods.make import Make
from ..methods.users_groups import UserMethod, GroupMethod
from ..controllers.service import Service

_CONF_DIR = path.join(path.dirname(__file__), "config")

_BASE = {
    "httpd": {
        "method": PackageManager,
        "controller": Service,
        "type": base.HTTPD
    },
    "esgf-httpd.conf": {
        "method": FileManager,
        "type": FileComponent,
        "requires": ["httpd"],
        "source": path.join(_CONF_DIR, "httpd", "{name}"),
        "dest": path.join(os.sep, "etc", "httpd", "conf", "httpd.conf")
    },
    "esgf-ca-bundle.crt": {
        "method": FileManager,
        "type": FileComponent,
        "source": path.join(_CONF_DIR, "httpd", "{name}"),
        "dest": path.join(os.sep, "etc", "certs", "{name}")
    },
    "postgres": {
        "method": PackageManager,
        "controller": Service,
        "service_name": "postgresql",
        "type": base.Postgres,
        "version": "8.4.20",
        "pkg_names": {
            "yum": "postgresql-server-{version}"
        }
    },
    "postgres-init": {
        "method": Command,
        "type": CommandComponent,
        "requires": "postgres",
        "command": "service",
        "args": ["postgresql", "initdb"]
    },
    "postgresql.conf": {
        "method": FileManager,
        "type": FileComponent,
        "requires": ["postgres-init"],
        "source": path.join(_CONF_DIR, "postgres", "{name}"),
        "dest": path.join(os.sep, "var", "lib", "pgsql", "data", "{name}"),
        "owner": {
            "user": "postgres",
            "group": "postgres"
        }
    },
    "pg_hba.conf": {
        "method": FileManager,
        "type": FileComponent,
        "requires": ["postgres-init"],
        "source": path.join(_CONF_DIR, "postgres", "{name}"),
        "dest": path.join(os.sep, "var", "lib", "pgsql", "data", "{name}"),
        "owner": {
            "user": "postgres",
            "group": "postgres"
        }
    },
    "java": {
        "method": PackageManager,
        "type": SysPkgComponent,
        "version": "1.8.0",
        "pkg_names": {
            "yum": "java-{version}-openjdk"
        }
    },
    "postgresql-devel": {
        "method": PackageManager,
        "type": SysPkgComponent
    },
    "httpd-devel": {
        "method": PackageManager,
        "type": SysPkgComponent
    },
    "mod_ssl": {
        "method": PackageManager,
        "type": SysPkgComponent
    },
    # "sqlite-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "freetype-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "curl-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "bison": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "file": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "flex": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "uuid-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libtool": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "gettext-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libuuid-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libxml2": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libxml2-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libxslt": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libxslt-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "lsof": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "openssl-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "pam-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "pax": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "tk-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "zlib-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "perl-Archive-Tar": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "perl-XML-Parser": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libX11-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libtool-ltdl-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "e2fsprogs-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "gcc-gfortran": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libicu-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libgtextutils-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "libjpeg-turbo-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "*ExtUtils*": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "readline-devel": {
    #     "method": PackageManager,
    #     "type": SysPkgComponent
    # },
    # "java": {
    #     "type": base.Java,
    #     "version": "1.8.0_162",
    #     "url": "http://aims1.llnl.gov/esgf/dist/2.6/8/java/{version}/jdk{version}-64.tar.gz",
    #     "extract_dir": "/tmp/java",
    #     "tar_root_dir": "jdk{version}"
    # },
    "tomcat-group": {
        "method": GroupMethod,
        "type": GroupComponent,
        "groupname": "tomcat"
    },
    "tomcat-user": {
        "method": UserMethod,
        "type": UserComponent,
        "requires": ["tomcat-group"],
        "options": ["-s", "/sbin/nologin", "-g", "tomcat", "-d", "/usr/local/tomcat"],
        "username": "tomcat"
    },
    "tomcat": {
        "method": FileManager,
        "type": FileComponent,
        "requires": ["tomcat-user", "tomcat-group"],
        "version": "8.5.20",
        "source": "http://archive.apache.org/dist/tomcat/tomcat-8/v{version}/bin/apache-tomcat-{version}.tar.gz",
        "dest": "/tmp/tomcat",
        "tar_root_dir": "apache-tomcat-{version}",
        "owner": {
            "user": "tomcat",
            "group": "tomcat"
        }
    }
    # "esgf-config-git": {
    #     "method": Git,
    #     "type": FileComponent,
    #     "source": "https://github.com/ESGF/esgf-config.git",
    #     "dest": "/tmp/esgf-config"
    # }
}
_DATA = {
    "thredds": {
        "method": FileManager,
        "type": data.Thredds,
        "version": "5.0.2",
        "source": "https://aims1.llnl.gov/esgf/dist/2.6/8/thredds/5.0/{version}/thredds.war",
        "dest": "/tmp/thredds"
    },
    "esgf-dashboard-git": {
        "method": Git,
        "type": FileComponent,
        "tag": "v1.5.20",
        "source": "https://github.com/ESGF/esgf-dashboard.git",
        "dest": "/tmp/esgf-dashboard"
    },
    "cdutil": {
        "method": Conda,
        "type": CondaComponent,
        "channels": ["conda-forge"]
    },
    "cmor": {
        "method": Conda,
        "type": CondaComponent,
        "channels": ["conda-forge"]
    },
    "esgcet": {
        "method": Pip,
        "type": PipComponent,
        "requires": ["postgres", "postgresql-devel"],
        "version": "3.5.0",
        "tag": "v{version}",
        "repo": "https://github.com/ESGF/esg-publisher.git",
        "egg": "{name}",
        "subdirectory": "src/python/esgcet",
        "pip_name": "git+{repo}@{tag}#egg={egg}&subdirectory={subdirectory}"
    },
    "esgf-dashboard": {
        "method": EasyInstall,
        "type": FileComponent,
        "version": "0.0.2",
        "source": "http://aims1.llnl.gov/esgf/dist/2.6/8/esgf-dashboard/esgf_dashboard-{version}-py2.7.egg",
        "dest": "/tmp/esgf_dashboard/esgf_dashboard.egg",
        "extract": False
    },
    "esgf-node-manager": {
        "method": EasyInstall,
        "type": FileComponent,
        "version": "0.1.5",
        "source": "http://aims1.llnl.gov/esgf/dist/2.6/8/esgf-node-manager/esgf_node_manager-{version}-py2.7.egg",
        "dest": "/tmp/esgf_node_manager/esgf_node_manager.egg",
        "extract": False
    }
}
_INDEX = {
    "transfer_api_client_python-mkproxy": {
        "method": Make,
        "type": MakeComponent,
        "source": "https://github.com/globusonline/transfer-api-client-python.git",
        "dest": "/usr/local/cog/transfer-api-client-python",
        "make_dir": "{dest}/mkproxy"
    },
    "mod-wsgi": {
        "method": Pip,
        "type": PipComponent,
        "requires": ["httpd"],
        "version": "4.5.3",
        "pip_name": "{name}=={version}"
    },
    "django-openid-auth": {
        "method": Pip,
        "type": PipComponent,
        "repo": "https://github.com/EarthSystemCoG/django-openid-auth.git",
        "egg": "{name}",
        "pip_name": "git+{repo}#egg={egg}"
    }
}
ALL = {
    "base": _BASE,
    "data": _DATA,
    "index": _INDEX
}