# ESGF Installer
The ESGF Installer is a command line tool for installing the ESGF Software Stack.  
The software stack is comprised of: Tomcat, Thredds, CDAT & CDMS, PostgreSQL, MyProxy, and several ESGF.org custom software applications running on a LINUX (RedHat/CentOS) operating system.

The custom ESGF software includes:
- [ESGF-dashboard](https://github.com/ESGF/esgf-dashboard)
- [ESGF-publisher](https://github.com/ESGF/esg-publisher)
- [ESGF-node-manager](https://github.com/ESGF/esgf-node-manager)
- [ESGF-stats-api](https://github.com/ESGF/esgf-stats-api)
- [ESGF-search](https://github.com/ESGF/esg-search)
- [ESGF-idp](https://github.com/ESGF/esgf-idp)
- [ESGF-orp](https://github.com/ESGF/esg-orp)
- [ESGF-security](https://github.com/ESGF/esgf-security)
- [ESGF-SLCS-server](https://github.com/ESGF/esgf-slcs-server)

## Installation
Clone this repo using ```git clone https://github.com/ESGF/esgf-installer.git```
Install Miniconda by running the ```install_conda.sh``` script
Activate the ```esgf-pub``` conda environment using ```source /usr/loca/conda/bin/activate esgf-pub```
Run an installation by invoking the ```esg_node.py``` script.
- Example: ```python esg_node.py --install --type data```



More detailed installation instructions can be found on the [wiki](https://github.com/ESGF/esgf-installer/wiki)

## Support

Please [open an issue](https://github.com/ESGF/esgf-installer/issues/new) for support.
Please follow the [Issue Tracking Guidelines](https://github.com/ESGF/esgf-installer/wiki/ESGF-Installer-Issue-Tracking-Guidelines) when opening a new issue.


## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/ESGF/esgf-installer/compare).
