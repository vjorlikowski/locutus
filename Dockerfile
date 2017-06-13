#
# Locutus SDN Controller Dockerfile
#

# Pull base image.
FROM python:2

# Grab latest version of locutus, unpack it, install dependencies, and install it.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python-pip \
      wget \
      unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    wget -O /opt/locutus.zip "https://github.com/vjorlikowski/locutus/archive/master.zip" --no-check-certificate && \
    unzip -q /opt/locutus.zip -d /opt && \
    mv /opt/locutus-master /opt/locutus && \
    rm /opt/locutus.zip && \
    cd /opt/locutus && \
    pip install -r pip-requires && \
    python ./setup.py install

# Add the locutus user and group
RUN useradd -ms /sbin/nologin locutus

# Change ownership of the log directory
RUN chown -R locutus:locutus /var/log/locutus

# Define ports
EXPOSE 6633 8080

# Change user, and run.
USER locutus
ENTRYPOINT /usr/local/bin/ryu run --config-file /etc/locutus/ryu.conf
