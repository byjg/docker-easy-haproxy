FROM haproxy:1.8-alpine

RUN apk add --no-cache bash

COPY *.sh /
COPY conf.d /etc/haproxy/conf.d
COPY assets/errors-custom/* /etc/haproxy/errors-custom/

ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["haproxy", "-f", "/etc/haproxy/haproxy.cfg"]