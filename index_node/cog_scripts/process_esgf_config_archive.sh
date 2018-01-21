#!/bin/bash

echo "untar esgf config files"
mkdir -p /esg
tar --same-owner -pxaf /root/archives/esgf_config.tar.xz -C /esg

echo "set permissions"
chmod 644 /esg/config/*
#chown root:tomcat /esg/config/.esg*
chmod 640 /esg/config/.esg*

#chown -R tomcat:tomcat /esg/config/tomcat
chmod 755 /esg/config/tomcat
chmod 600 /esg/config/tomcat/*

chmod 755 /esg/config/esgcet
chmod 644 /esg/config/esgcet/*
chmod 640 /esg/config/esgcet/esg.ini