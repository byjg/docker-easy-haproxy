FROM alpine:3.18

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG
ENV TZ="Etc/UTC"

WORKDIR /scripts

COPY src/ /scripts/
COPY build/assets /

RUN apk add --no-cache haproxy bash python3 py3-pip py-yaml certbot openssl \
 && pip3 install --upgrade pip \
 && pip install -r requirements.txt \
 && pytest -s -vv tests/ \
 && openssl dhparam -out /etc/haproxy/dhparam 2048 \
 && openssl dhparam -out /etc/haproxy/dhparam-1024 1024

CMD ["/usr/bin/python", "-u", "/scripts/main.py" ]
