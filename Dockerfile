FROM ubuntu:20.04

MAINTAINER akshata.mahamuni@paroscale.com
RUN apt-get update \
    && apt-get install -y git \
    && apt-get -y install python3-pip \
    && pip3 install ansible

WORKDIR /opt

COPY . /opt

RUN ansible-playbook msg.yml
