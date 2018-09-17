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

defaults() {
echo "
defaults
    log global

    timeout connect    3s
    timeout client    10s
    timeout server    10m

    errorfile 400 /etc/haproxy/errors-custom/400.http
    errorfile 403 /etc/haproxy/errors-custom/403.http
    errorfile 408 /etc/haproxy/errors-custom/408.http
    errorfile 500 /etc/haproxy/errors-custom/500.http
    errorfile 502 /etc/haproxy/errors-custom/502.http
    errorfile 503 /etc/haproxy/errors-custom/503.http
    errorfile 504 /etc/haproxy/errors-custom/504.http

global
    log /dev/log local0
    maxconn 2000
"
}

stats() {
echo "
frontend stats
    bind *:1936
    mode http
    stats enable
    stats hide-version
    stats realm Haproxy\ Statistics
    stats uri /
    stats auth $1:$2
#    acl is_proxystats hdr_dom(host) -i some.host.com
#    default_backend srv_stats
    use_backend srv_stats if is_proxystats

backend srv_stats
    mode http
    server Local 127.0.0.1:1936
"
}

frontend() {
    echo "
frontend http_in
    bind *:80
    mode http
"

    COUNT=1
    for FEACL in `echo $1`
    do
        echo "    acl is_rule_$COUNT hdr_dom(host) -i -m end $FEACL"
        COUNT=$((COUNT + 1))
    done
    echo
    COUNT=1
    for FEACL in `echo $1`
    do
        echo "    use_backend srv_80_$COUNT if is_rule_$COUNT"
        COUNT=$((COUNT + 1))
    done
}

backend () {
    COUNT=1
    for BESRV in `echo $1`
    do
        echo "
backend srv_80_$COUNT
    balance roundrobin
    mode http
    option forwardfor
    http-request set-header X-Forwarded-Port %[dst_port]
    http-request add-header X-Forwarded-Proto https if { ssl_fc }
"
        echo "    server srv $BESRV check weight 1"
        COUNT=$((COUNT + 1))
    done
}


HAPROXY_CFG="/etc/haproxy/haproxy.cfg"
FRONTEND=""
BACKEND=""
TURN="FB"
for LB_HOST in `echo ${LB_HOSTS}`;
do
    if [ "$TURN" == "FB" ]
    then
        FRONTEND="$FRONTEND $LB_HOST"
        TURN="BE"
        continue
    fi

    if [ "$TURN" == "BE" ]
    then
        BACKEND="$BACKEND $LB_HOST"
        TURN="FB"
        continue
    fi
done

# Write
defaults > ${HAPROXY_CFG}
if [ ! -z "${LB_STATS_USER}" ]
then
    stats ${LB_STATS_USER} ${LB_STATS_PASS} >> ${HAPROXY_CFG}
fi
frontend "$FRONTEND" >> ${HAPROXY_CFG}
backend "$BACKEND" >> ${HAPROXY_CFG}

# More
for config in `ls /etc/haproxy/conf.d/*.cfg`
do
    echo Loading extra config: ${config}
    cat ${config} >> ${HAPROXY_CFG}
done

echo

/sbin/syslogd -O /proc/1/fd/1
/docker-entrypoint.sh "$@"
