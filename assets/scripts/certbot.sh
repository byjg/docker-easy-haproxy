#!/usr/bin/env bash

mkdir -p /var/log/letsencrypt
ln -sf /dev/stdout  /var/log/letsencrypt/letsencrypt.log

REQUEST_CERTS=""
RENEW_CERTS=""

for domain in $(cat /scripts/letsencrypt_hosts.txt); do
    if [ ! -f "/etc/haproxy/certs/$domain.pem" ]; then
        REQUEST_CERTS="$REQUES_CERTS -d $domain"
        continue
    fi

    if [[ $(find "/etc/haproxy/certs/$domain.pem" -mtime +30 -print) ]]; then
        RENEW_CERTS="$RENEW_CERTS -d $domain"
    fi
done

if [ -n "$REQUEST_CERTS" ]; then
    certbot certonly \
        --standalone \
        --preferred-challenges http \
        --http-01-port 2080 \
        --agree-tos \
        --issuance-timeout 90 \
        --no-eff-email \
        --non-interactive \
        --max-log-backups=0 \
        --post-hook "/scripts/certbot_to_haproxy.sh" \
        $REQUEST_CERTS --email info@xpto.us 
fi

if [ -n "$RENEW_CERTS" ]; then
    certbot renew --post-hook "/scripts/certbot_to_haproxy.sh"
fi