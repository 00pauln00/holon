# Container image that runs your code
FROM ubuntu:20.04
MAINTAINER vishwambhar.kapare@paroscale.com
RUN apt-get update \
    && apt-get -y install python3-pip \
    && pip3 install ansible

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY entrypoint.sh /entrypoint.sh
WORKDIR /app
COPY hello_world.yml /app

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]
RUN ansible-playbook hello_world.yml
