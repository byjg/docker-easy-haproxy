FROM haproxy:1.9-alpine

RUN apk add --no-cache bash python3 py-yaml

COPY entrypoint.* /
COPY conf.d /etc/haproxy/conf.d
COPY assets/errors-custom/* /etc/haproxy/errors-custom/
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["haproxy", "-f", "/etc/haproxy/haproxy.cfg"]