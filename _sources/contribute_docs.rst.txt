Contributing to Documentation
******************************************
The steps for adding new documentation to the ESGF Installer documentation page are as follows

1. Create a new ReStructured Text (rst) file named as {doc_name.rst}.  Example: the API page is named api.rst
2. Populate the file with the relevant documentation information
3. Edit the index.rst file to reference the newly created rst file.  Example:  Look for the relevant table of contents section (toctree) or create a new one.  The add the file name (with no extension) underneath the toctree section
4. Run the ```push_to_github.sh``` script to build the new html pages and upload them to Github Pages.
