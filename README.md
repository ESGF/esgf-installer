# ESGF Installer
The ESGF Installer is a command line tool for installing the ESGF Software Stack.  
The software stack is comprised of: Tomcat, Thredds, CDAT & CDMS, PostgreSQL, MyProxy, and several ESGF custom software applications running on a LINUX (RedHat/CentOS) operating system.

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
The installation is performed on the Node itself.
### Clone
Clone this repo using 
```
git clone https://github.com/ESGF/esgf-installer.git && cd esgf-installer
```
### Checkout
Checkout the appropriate branch/tag. For example, the 3.0 beta version can be accessed with the following command: 
```
git checkout tags/v3.0b1 -b 3.0_beta
```
This will checkout out the beta release tag and create a new branch called 3.0_beta.

### Configure
Note that, to avoid being prompted for various parameters, the `esgf.properties.template` should be populated with the proper values for your node.

See [the properties file documentation](https://esgf.github.io/esgf-installer/autoinstall_usage.html) for information when populating.

### Bootstrap and Activate
Install Miniconda and other ESGF dependencies from yum and pip by running the bootstrap script:
```
./esg_bootstrap.sh
```
If you are migrating to ESGF 3.0 from a previous version of ESGF, add the migrate parameter to the the bootstrap
```
./esg_bootstrap.sh migrate
```
Activate the esgf-pub conda environment
```
source /usr/local/conda/bin/activate esgf-pub
```

### Install
Run an installation by invoking the `esg_node.py` script. For example, a data-only node installation:
```
python esg_node.py --install --type data
```


More detailed installation instructions can be found on the [wiki](https://github.com/ESGF/esgf-installer/wiki)

## API Documentation
- [ESGF 3.0 API Documentation](https://esgf.github.io/esgf-installer/)

## Support

Please [open an issue](https://github.com/ESGF/esgf-installer/issues/new) for support.
Please follow the [Issue Tracking Guidelines](https://github.com/ESGF/esgf-installer/wiki/ESGF-Installer-Issue-Tracking-Guidelines) when opening a new issue.


## Contributing

Please contribute using [Github Flow](https://guides.github.com/introduction/flow/). Create a branch, add commits, and [open a pull request](https://github.com/ESGF/esgf-installer/compare).
