FROM alpine:3.20

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG
ENV TZ="Etc/UTC"

RUN apk add --no-cache haproxy bash python3 py3-pip py-yaml certbot openssl \
    && pip3 install --upgrade pip --break-system-packages

RUN openssl dhparam -out /etc/haproxy/dhparam 2048 \
    && openssl dhparam -out /etc/haproxy/dhparam-1024 1024

WORKDIR /scripts

COPY build/assets /

COPY src/ /scripts/

RUN pip install -r requirements.txt --break-system-packages

RUN pytest -s -vv tests/

CMD ["/usr/bin/python", "-u", "/scripts/main.py" ]
