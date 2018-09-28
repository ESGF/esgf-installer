import base
import data
from .files import FileComponent
from .syspkg import SysPkgComponent
from .pip import PipComponent
from .make import MakeComponent
from ..methods.distribution import FileManager
from ..methods.package_manager import PackageManager, Pip
from ..methods.easy_install import EasyInstall
from ..methods.make import Make
from ..controllers.service import Service

_BASE = {
    "httpd": {
        "method": PackageManager,
        "controller": Service,
        "type": base.HTTPD
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
    "tomcat": {
        "method": FileManager,
        "type": FileComponent,
        "version": "8.5.20",
        "source": "http://archive.apache.org/dist/tomcat/tomcat-8/v{version}/bin/apache-tomcat-{version}.tar.gz",
        "dest": "/tmp/tomcat",
        "tar_root_dir": "apache-tomcat-{version}"
    },
    "esgf-config-git": {
        "method": FileManager,
        "type": FileComponent,
        "source": "https://github.com/ESGF/esgf-config.git",
        "dest": "/tmp/{name}"
    }
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
        "method": FileManager,
        "type": FileComponent,
        "tag": "v1.5.20",
        "source": "https://github.com/ESGF/esgf-dashboard.git",
        "dest": "/tmp/{name}"
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
