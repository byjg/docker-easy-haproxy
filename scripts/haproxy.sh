#!/usr/bin/env bash

/usr/local/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -S /var/run/haproxy.sock

while true; do
    sleep 60
done
