FROM haproxy:2.1-alpine

WORKDIR /scripts

RUN apk add --no-cache bash python3 py-yaml supervisor docker

COPY requirements.txt /scripts
RUN pip3 install --upgrade pip \
 && pip install -r requirements.txt

COPY templates /scripts/templates/
COPY easymapping /scripts/easymapping/

COPY assets /

CMD ["/usr/bin/supervisord",  "-n",  "-c", "/etc/supervisord.conf" ]
