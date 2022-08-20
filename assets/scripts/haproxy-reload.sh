#!/usr/bin/env bash

source /scripts/functions.sh

cd /scripts

RELOAD="true"

if [[ "static|docker|swarm" != *"$EASYHAPROXY_DISCOVER"* ]];then
    log "info" "CONF_CHECK" "ERROR: EASYHAPROXY_DISCOVER should be 'static', 'docker', or 'swarm'. I got '$EASYHAPROXY_DISCOVER' instead."
    exit 1
fi

if [[ "$EASYHAPROXY_DISCOVER" == "static" ]]; then
    CONTROL_FILE="/etc/haproxy/haproxy.cfg"
    touch ${CONTROL_FILE}
    cp ${CONTROL_FILE} ${CONTROL_FILE}.old
    python3 static.py /etc/haproxy/easyconfig.yml > ${CONTROL_FILE}
else
    CONTROL_FILE="/tmp/.docker_data"
    touch ${CONTROL_FILE}
    mv ${CONTROL_FILE} ${CONTROL_FILE}.old
    touch ${CONTROL_FILE}

    if [[ "$EASYHAPROXY_DISCOVER" == "docker" ]]; then
        CONTAINERS=$(docker ps -q | sort | uniq)
        LABEL_PATH=".Config.Labels"

        for container in ${CONTAINERS}; do
            docker inspect --format "{{ json $LABEL_PATH }}" ${container} | xargs -I % echo ${container}=% >> ${CONTROL_FILE}
        done
    else
        CONTAINERS=$(docker node ps $(docker node ls -q) --format "{{ .Name }}" --filter desired-state=running | cut -d. -f1 | sort | uniq)
        LABEL_PATH=".Spec.Labels"

        for container in ${CONTAINERS}; do
            docker service inspect --format "{{ json $LABEL_PATH }}" ${container} | xargs -I % echo ${container}=% >> ${CONTROL_FILE}
        done
    fi

    if cmp -s ${CONTROL_FILE} ${CONTROL_FILE}.old ; then
        RELOAD="false"
    else
        python3 swarm.py > /etc/haproxy/haproxy.cfg
	log "info" "CONF_CHECK" "New configuration found"
    fi
fi

if cmp -s ${CONTROL_FILE} ${CONTROL_FILE}.old ; then
    RELOAD="false"
fi

if [[ ! -z "$1" ]]; then
    log "info" "CONF_CHECK" "Initial configuration. Skip certbot."
else
    /scripts/certbot.sh
fi

# If Certbot reloads successfully will create the file /tmp/force-reload
if [ -f /tmp/force-reload ]; then
    log "info" "CONF_CHECK" "New certificates found..."
    RELOAD="true"
    rm /tmp/force-reload
fi

if [[ ! -z "$1" ]]; then
    log "info" "CONF_CHECK" "Starting haproxy..."
    /usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg $(ls /etc/haproxy/conf.d/*.cfg 2>/dev/null | xargs -I{} echo -f {}) -p /run/haproxy.pid -S /var/run/haproxy.sock &

elif [[ "$RELOAD" == "true" ]]; then
    log "info" "CONF_CHECK" "Reloading..."
    /usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg $(ls /etc/haproxy/conf.d/*.cfg 2>/dev/null | xargs -I{} echo -f {}) -p /run/haproxy.pid -x /var/run/haproxy.sock -sf $(cat /run/haproxy.pid) &
fi
