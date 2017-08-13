# Docker image based on Centos 6 for running the ESGF autoinstaller for continous integration

FROM centos:6

MAINTAINER William Hill <hill119@llnl.gov>

WORKDIR /usr/local/bin

RUN yum -y update

RUN cd /usr/local/bin && pwd

RUN yum -y install wget

RUN wget -O esg-bootstrap http://distrib-coffee.ipsl.jussieu.fr/pub/esgf/dist/devel/esgf-installer/2.5/esg-bootstrap --no-check-certificate

RUN chmod 555 esg-bootstrap;

RUN bash esg-bootstrap --devel;

RUN ls -lah