ESGF Command Line Interface
******************************************

This program must be run as root or a root equivalent shell: (sudo -s)

.. argparse::
   :ref: esgf_utilities.esg_cli.argparser
   :prog: esg_node.py


NOTE:

You must be root or effectively root to run this program,
prefixing the command with sudo will not allow the use of
needed environment variables!!!! If you must use sudo, do so
only to become root proper then source your user's .[bash]rc
file so that root has it's environment set accordingly!  Or you
can more simply become root using sudo's \"-s\" flag.  After a
full install there will be a file created (/etc/esg.env) that has
the basic environment vars that were used and set during the
installation - this should be sourced by users of this
application stack.
