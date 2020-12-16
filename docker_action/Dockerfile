# Container image that runs your code
FROM ubuntu:18.04
MAINTAINER vishwambhar.kapare@paroscale.com

RUN apt-get update -y \
    && apt-get -y install libaio-dev openssl libk5crypto3 librocksdb5.8 uuid vim python3-pip \
    && pip3 install func_timeout sockets psutil dpath \
    && pip3 install ansible \
    && pip3 install jmespath

# Copies your code file from your action repository to the filesystem path `/` of the container
COPY entrypoint.sh /entrypoint.sh
WORKDIR /app
COPY hello_world.yml /app

# Code file to execute when the docker container starts up (`entrypoint.sh`)
ENTRYPOINT ["/entrypoint.sh"]
RUN ansible-playbook hello_world.yml
