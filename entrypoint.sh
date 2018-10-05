#!/usr/bin/env bash

set -e

echo " ______                  _    _          _____                     "
echo "|  ____|                | |  | |   /\   |  __ \                    "
echo "| |__   __ _ ___ _   _  | |__| |  /  \  | |__) | __ _____  ___   _ "
echo "|  __| / _\` / __| | | | |  __  | / /\ \ |  ___/ '__/ _ \ \/ / | | |"
echo "| |___| (_| \__ \ |_| | | |  | |/ ____ \| |   | | | (_) >  <| |_| |"
echo "|______\__,_|___/\__, | |_|  |_/_/    \_\_|   |_|  \___/_/\_\\__, |"
echo "                  __/ |                                       __/ |"
echo "                 |___/                                       |___/ "
echo ""

HAPROXY_CFG="/etc/haproxy/haproxy.cfg"
EASYCONFIG_CFG="/etc/easyconfig/easyconfig.cfg"

if [ ! -f "$EASYCONFIG_CFG" ]
then
    echo "File '$EASYCONFIG_CFG' does not exist"
    exit 1
fi



python3 /entrypoint.py "$EASYCONFIG_CFG" > $HAPROXY_CFG


/sbin/syslogd -O /proc/1/fd/1
/docker-entrypoint.sh "$@"
