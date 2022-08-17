#!/usr/bin/env bash

/usr/sbin/haproxy -v

source /scripts/haproxy-reload.sh initial

while true; do
    sleep 60
done
