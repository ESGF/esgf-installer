Installation
******************************************

1. Clone this repo using ``git clone https://github.com/ESGF/esgf-installer.git``
2. Change directory to the ``installer/`` directory
3. If Miniconda has not been installed, install Miniconda by running the ``install_conda.sh`` script
4. Activate the esgf-pub conda environment using ``source /usr/local/conda/bin/activate esgf-pub``
5. Install dependencies from pip using the requirements.txt with the command ``pip install -r requirements.txt``
6. Run an installation by invoking the ``esg_node.py`` script.
   Example: ``python esg_node.py --install --type data``
