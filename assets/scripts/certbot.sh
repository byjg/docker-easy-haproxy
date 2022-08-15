#!/usr/bin/env bash

@todo

ln -sf /dev/stdout  /var/log/letsencrypt/letsencrypt.log

certbot certonly \
    --standalone \
    --preferred-challenges http \
    --http-01-port 2080 \
    --agree-tos \
    --issuance-timeout 90 \
    --no-eff-email \
    --non-interactive \
    --max-log-backups=0 \
    --post-hook "/scripts/certbot_to_haproxy.sh && systemctl reload haproxy.service"
    -d dev.globalnetguide.com -d other.domain.com --email info@xpto.us 
