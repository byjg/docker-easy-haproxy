FROM alpine:3.14

WORKDIR /scripts

RUN apk add --no-cache haproxy bash python3 py3-pip py-yaml supervisor docker \
 && ln -s /usr/bin/python3 /usr/bin/python

COPY requirements.txt /scripts

RUN pip3 install --upgrade pip \
 && pip install -r requirements.txt

COPY templates /scripts/templates/
COPY easymapping /scripts/easymapping/
COPY tests/ /scripts/tests/

COPY assets /

RUN pytest -s tests/

CMD ["/usr/bin/supervisord",  "-n",  "-c", "/etc/supervisord.conf" ]
