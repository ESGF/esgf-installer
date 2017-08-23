# ESGF Installer
The ESGF Installer is a command line tool for installing the ESGF Software Stack.  
The software stack is comprised of: Tomcat, Thredds, CDAT & CDMS, PostgreSQL, MyProxy, and several ESGF.org custom software applications running on a LINUX (RedHat/CentOS) operating system.

## Installation
To setup a 'devel' install 
 
    cd /usr/local/bin
    wget -O esg-bootstrap http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/devel/esgf-installer/2.5/esg-bootstrap --no-check-certificate  
    chmod 555 esg-bootstrap  
    ./esg-bootstrap --devel   
 
To setup a 'master' install  
 
    wget -O esg-bootstrap http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/esgf-installer/2.4/esg-bootstrap --no-check-certificate  
    chmod 555 esg-bootstrap  
    ./esg-bootstrap    
