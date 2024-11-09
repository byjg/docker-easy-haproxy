FROM alpine:3.18

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG
ENV TZ="Etc/UTC"

RUN apk add --no-cache haproxy bash python3 py3-pip py-yaml certbot openssl \
    && pip3 install --upgrade pip

RUN openssl dhparam -out /etc/haproxy/dhparam 2048 \
    && openssl dhparam -out /etc/haproxy/dhparam-1024 1024

WORKDIR /scripts

COPY build/assets /

COPY src/ /scripts/

RUN pip install -r requirements.txt

RUN pytest -s -vv tests/

CMD ["/usr/bin/python", "-u", "/scripts/main.py" ]
