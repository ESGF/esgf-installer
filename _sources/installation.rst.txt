**ESGF 3.0 currently supports RHEL/CentOS 6**

Installation
******************************************

1. Clone this repo using ``git clone https://github.com/ESGF/esgf-installer.git``
2. Checkout the appropriate branch/tag. For example, the 3.0 alpha version can be accessed with the following command: ``git checkout tags/v3.0.0-alpha-release -b 3.0_alpha``.
   This will checkout out the alpha release tag and create a new branch called 3.0_alpha
3. If Miniconda has not been installed, install Miniconda and other ESGF dependencies from yum and pip by running the ``esg_bootstrap.sh`` script
4. Activate the esgf-pub conda environment using ``source /usr/local/conda/bin/activate esgf-pub``
5. Run an installation by invoking the ``esg_node.py`` script.
   Example: ``python esg_node.py --install --type data``


Autoinstaller
**************************

Instead of answering prompts interactively on the command line, there is an option for configuring a node using a configuration file.

1. Complete steps 1-4 listed above
2. Edit the ```/esg/config/esgf.properties``` file with your node configuration.
3. Run an installation by invoking the ``esg_node.py`` script. Example: ``python esg_node.py --install --type data``
