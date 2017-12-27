Installation
******************************************

1. Clone this repo using ``git clone https://github.com/ESGF/esgf-installer.git``
2. Change directory to the ``installer/`` directory
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
