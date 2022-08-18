#!/usr/bin/env bash

/usr/sbin/haproxy -v

if [ -z "$EASYHAPROXY_DATEFORMAT" ]; then
    export EASYHAPROXY_DATEFORMAT="%Y-%m-%d %H:%M:%S %Z"
fi

if [ -z "$EASYHAPROXY_REFRESH_CONF" ]; then
    export EASYHAPROXY_REFRESH_CONF=10
fi

/scripts/haproxy-reload.sh initial

while true; do
    sleep $EASYHAPROXY_REFRESH_CONF
    echo "[CONF_CHECK] $(date +"$EASYHAPROXY_DATEFORMAT") - Heartbeat."
    /scripts/haproxy-reload.sh
done
