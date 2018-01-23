#!/bin/bash
# script containing env variables for starting ESGF Tomcat

export JAVA_OPTS="-Dtds.content.root.path=/esg/content"

#Sets the Java binary for Tomcat to use
export JAVA_HOME="/usr/local/java"

#export JAVA_OPTS="-Djavax.net.debug=ssl -Dtds.content.root.path=/esg/content"
#export CATALINA_OPTS="-Xmx2048m -server -Xms1024m -XX:MaxPermSize=512m -Dsun.security.ssl.allowUnsafeRenegotiation=false -Djavax.net.ssl.trustStore='/esg/config/tomcat/esg-truststore.ts' -Djavax.net.ssl.trustStorePassword='changeit'"
# IMPORTANT : when running on single host, Tomcat will be killed if it exceeds the memory limits
export CATALINA_OPTS="-Xmx512m -server -Xms512m -XX:MaxPermSize=512m -Dsun.security.ssl.allowUnsafeRenegotiation=false -Djavax.net.ssl.trustStore='/esg/config/tomcat/esg-truststore.ts' -Djavax.net.ssl.trustStorePassword='changeit'"
export CATALINA_PID="/tmp/catalina.pid"
