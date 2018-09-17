FROM haproxy:1.8-alpine

RUN apk add --no-cache bash

COPY entrypoint.sh /

ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]