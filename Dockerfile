FROM haproxy:1.9-alpine

WORKDIR /root

RUN apk add --no-cache bash python3 py-yaml supervisor docker

COPY requirements.txt /root
RUN pip3 install --upgrade pip \
 && pip install -r requirements.txt


COPY haproxy.cfg /etc/haproxy/haproxy.cfg
COPY conf.d /etc/haproxy/conf.d
COPY assets/errors-custom/* /etc/haproxy/errors-custom/
COPY assets/supervisord.conf /etc/supervisord.conf
COPY assets/crontab /etc/crontabs/root

COPY scripts/exit-event-listener.py /exit-event-listener.py
COPY scripts/haproxy.sh /haproxy.sh
COPY scripts/haproxy-reload.sh /haproxy-reload.sh


#CMD ["haproxy", "-f", "/etc/haproxy/haproxy.cfg"]
CMD ["/usr/bin/supervisord",  "-n",  "-c", "/etc/supervisord.conf" ]