FROM alpine:3.16

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG

WORKDIR /scripts

COPY src/ /scripts/
COPY assets /

RUN apk add --no-cache haproxy bash python3 py3-pip py-yaml docker certbot openssl \
 && ln -s /usr/bin/python3 /usr/bin/python \
 && pip3 install --upgrade pip
#   \
#  && pip install -r requirements.txt \
#  && pytest -s tests/ \
#  && openssl dhparam -out /etc/haproxy/dhparam 2048 \
#  && openssl dhparam -out /etc/haproxy/dhparam-1024 1024

# CMD ["/bin/bash", "-c", "/scripts/haproxy.sh" ]
