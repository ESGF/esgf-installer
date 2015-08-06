# WARNING: THIS SCRIPT WILL *COMPLETELY* UNINSTALL ALL ESGF SOFTWARE COMPONENTS FROM THIS NODE
# (to the best of our knowledge)
# WARNING: RUN THIS SCRIPT ONLY IF YOU WANT TO RE-INSTALL THE ESGF SOFTWARE STACK FROM SCRATCH

cd /usr/local
rm -rf esgf*
rm -rf cog
rm -rf globus
rm -rf las-esgf
rm -rf uvcdat
rm -rf ferret
rm -rf ferret_data
rm -rf apache-tomcat*
rm -rf pgsql
rm -rf solr*
unlink tomcat

cd /esg
rm -rf *
mkdir data

cd /etc
rm esg.env
unlink globus-host-ssl.conf
unlink globus-user-ssl.conf 
unlink grid-security.conf
rm -rf grid-security
rm -rf gridftp*
rm -rf myproxy*
rm -rf globus*
rm -rf gtk*


cd /root
rm -rf .globus/

cd /usr/local/bin
rm esg*

cd /usr/local/src
rm -rf esgf

rm /tmp/esgf_install.log

yum remove uvcdat globus* myproxy*
