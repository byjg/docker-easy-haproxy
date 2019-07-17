#!/usr/bin/env bash

echo "Reloading..."

/usr/local/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -x /var/run/haproxy.sock -sf $(cat /run/haproxy.pid) &