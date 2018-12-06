Autoinstaller Configuration Options
******************************************

The autoinstaller file, esgf.properties, can be used to configure options so that the install script will run with no further user input. Below are descriptions of the configuration options.  If an option is left blank, the user will be prompted for input for that option unless otherwise denoted.
Note that the file that the installer references for these properties is located at `/esg/config/esgf.properties` so make edits there after the initial population of the `esgf.properties.template`.

===============
Core Parameters
===============

.. topic:: esg.root.url

    The URL of the distribution mirror that will be used to fetch ESGF resources

.. topic:: esgf.host.ip 

    The IP address of the node

.. topic:: esgf.host

    The fully qualified domain name (fqdn) of your server

.. topic:: node.short.name

    Used to set the the Endpoint name in the Globus configuration (see: https://github.com/globus/globus-connect-server/blob/master/source/globus-connect-server.conf)

.. topic:: node.long.name

    More descriptive name of ESGF node (DEPRECATED)

.. topic:: node.namespace

    Set to your reverse fqdn Ex: gov.llnl (DEPRECATED)

.. topic:: node.peer.group

    <esgf-test | esgf-dev | esgf-prod>

    Determines the node's peer group, i.e which federation the node will belong to

.. topic:: esgf.index.peer

    Hostname of the index peer you wish to publish to

.. topic:: esgf.idp.peer

    Hostname of the IDP peer you wish to authenicate with

.. topic:: mail.admin.address

    Email address that will receive notifications from the ESGF server

.. topic:: publisher.db.user

    Name that will be created as a low privilege user account in Postgres for the ESGF Publisher

.. topic:: esg.org.name

    Organization name that is used as the root ID when running the esgsetup binary. Usually the name of the institution where the node is location (llnl, ipsl, etc.)

.. topic:: register.gridftp

    <y | yes | n | no>

    Determines if the GridFTP server will be registered with Globus

.. topic:: register.myproxy

    <y | yes | n | no>

    Determines if the MyProxy server will be registered with Globus

.. topic:: globus.user

    Your Globus Username

.. topic:: globus.password

    Your Globus Password

.. topic:: publisher.db.user

    Name that will be created as a low privilege user account in Postgres for the ESGF Publisher

============
Certificates
============

.. topic:: install.signed.certs

    <y | yes | n | no>

    Determines whether to install a commercially signed SSL certificate

.. topic:: commercial.key.path

    Absolute path to commercial key

.. topic:: commercial.cert.path

    Absolute path to commercially signed cert

.. topic:: cachain.path

    A comma separated list of the absolute paths that make up the cachain


==========
Update
==========

.. topic:: update.java

    <y | yes | n | no> 

    Determines whether to update Java if previous Java installation is found

.. topic:: update.ant

    <y | yes | n | no> 

    Determines whether to update Ant if previous Ant installation is found

.. topic:: backup.database

    <y | yes | n | no> 

    Determines whether to create a backup dump of the database if an existing Postgres installation is found

.. topic:: update.postgres

    <y | yes | n | no> 

    Determines whether to update Postgres if previous Postgres installation is found

.. topic:: update.apache

    <y | yes | n | no> 

    Determines whether to update Apache if previous Apache installation is found

.. topic:: update.tomcat

    <y | yes | n | no> 

    Determines whether to update Tomcat if previous Tomcat installation is found

.. topic:: update.orp

    <y | yes | n | no> 

    Determines whether to update ORP if previous ORP webapp installation is found

.. topic:: update.node.manager

    <y | yes | n | no> 

    Determines whether to update Node Manager if previous Node Manager webapp installation is found

.. topic:: update.thredds

    <y | yes | n | no> 

    Determines whether to update Thredds if previous Thredds webapp installation is found

.. topic:: update.dashboard

    <y | yes | n | no> 

    Determines whether to update Dashboard if previous Dashboard installation is found

.. topic:: update.publisher

    <y | yes | n | no> 

    Determines whether to update Publisher if previous Publisher installation is found

.. topic:: update.esg.search

    <y | yes | n | no> 

    Determines whether to update ESG Search if previous ESG Search webapp installation is found

.. topic:: update.cog

    <y | yes | n | no> 

    Determines whether to update CoG if previous CoG installation is found

.. topic:: update.solr

    <y | yes | n | no> 

    Determines whether to update Solr if previous Solr installation is found

.. topic:: backup.idp

    <y | yes | n | no> 

    Determines whether to update IDP if previous IDP webapp installation is found

.. topic:: update.globus

    <y | yes | n | no> 

    Determines whether to update Globus if previous Globus installation is found

.. topic:: update.slcs

    <y | yes | n | no> 

    Determines whether to update SLCS if previous SLCS server installation is found

=======================
Advanced User Settings
=======================

.. topic:: tomcat.user

    Name of tomcat user to be used with Thredds. Defaults to dnode_user if not populated

.. topic:: myproxy.endpoint

    Specifies the hostname of the myproxy-server
