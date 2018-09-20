import base
import data
from .distribution import DistComponent
from .syspkg import SysPkgComponent
from .pip import PipComponent
from ..methods.distribution import DistributionArchive
from ..methods.package_manager import PackageManager, Pip
# from .syspkg import PipComponent

_BASE = {
    PackageManager: {
        "httpd": {
            "type": base.HTTPD
        },
        "postgres": {
            "type": base.Postgres,
            "version": "8.4.20",
            "pkg_names": {
                "yum": "postgresql-server-{version}"
            }
        },
        "httpd-devel": {
            "type": SysPkgComponent
        },
        "mod_ssl": {
            "type": SysPkgComponent
        },
        "ant": {
            "type": SysPkgComponent
        },
        "java": {
            "type": SysPkgComponent,
            "version": "1.8.0",
            "pkg_names": {
                "yum": "java-{version}-openjdk"
            }
        }
    },
    DistributionArchive: {
        # "java": {
        #     "type": base.Java,
        #     "version": "1.8.0_162",
        #     "url": "http://aims1.llnl.gov/esgf/dist/2.6/8/java/{version}/jdk{version}-64.tar.gz",
        #     "extract_dir": "/tmp/java",
        #     "tar_root_dir": "jdk{version}"
        # },
        "tomcat": {
            "type": base.Tomcat,
            "version": "8.5.20",
            "url": "http://archive.apache.org/dist/tomcat/tomcat-8/v{version}/bin/apache-tomcat-{version}.tar.gz",
            "extract_dir": "/tmp/tomcat",
            "tar_root_dir": "apache-tomcat-{version}"
        }
    },
    Pip: {
        "mod_wsgi": {
            "type": PipComponent,
            "version": "4.5.3",
            "pip_name": "{name}=={version}"
        },
        "esgcet": {
            "type": PipComponent,
            "version": "3.5.0",
            "tag": "v{version}",
            "repo": "https://github.com/ESGF/esg-publisher.git",
            "egg": "{name}",
            "subdirectory": "src/python/esgcet",
            "pip_name": "git+{repo}@{tag}#egg={egg}&subdirectory={subdirectory}"
        },
        "django-openid-auth": {
            "type": PipComponent,
            "repo": "https://github.com/EarthSystemCoG/django-openid-auth.git",
            "egg": "{name}",
            "pip_name": "git+{repo}@{tag}#egg={egg}"
        }
    }
}
_DATA = {
    DistributionArchive: {
        "thredds": {
            "type": data.Thredds,
            "version": "5.0.2",
            "url": "https://aims1.llnl.gov/esgf/dist/2.6/8/thredds/5.0/{version}/thredds.war",
            "extract_dir": "/tmp/thredds"
        }
    }
}
ALL = {
    "base": _BASE,
    "data": _DATA
}
