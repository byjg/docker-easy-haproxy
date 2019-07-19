#!/usr/bin/env bash

cd /scripts

RELOAD="true"

if [[ "$DISCOVER" == "static" ]]; then
    CONTROL_FILE="/etc/haproxy/haproxy.cfg"
    touch ${CONTROL_FILE}
    cp ${CONTROL_FILE} ${CONTROL_FILE}.old
    python3 static.py /etc/haproxy/easyconfig.yml > ${CONTROL_FILE}
else
    CONTROL_FILE="/tmp/.docker_data"
    touch ${CONTROL_FILE}
    mv ${CONTROL_FILE} ${CONTROL_FILE}.old
    touch ${CONTROL_FILE}

    if [[ "$DISCOVER" == "docker" ]]; then
        CONTAINERS=$(docker ps -q)
        LABEL_PATH=".Config.Labels"
    else
        CONTAINERS=$(docker node ps $(docker node ls -q) --format "{{ .Name }}" --filter desired-state=running | cut -d. -f1 | sort | uniq)
        LABEL_PATH=".Spec.Labels"
    fi

    for container in ${CONTAINERS}; do
        docker inspect --format "{{ json $LABEL_PATH }}" ${container} | xargs -I % echo ${container}=% >> ${CONTROL_FILE}
    done

    if cmp -s ${CONTROL_FILE} ${CONTROL_FILE}.old ; then
        RELOAD="false"
    else
        python3 swarm.py > /etc/haproxy/haproxy.cfg
    fi
fi

if cmp -s ${CONTROL_FILE} ${CONTROL_FILE}.old ; then
    RELOAD="false"
fi

if [[ ! -z "$1" ]]; then
    echo "Initial configuration"
    RELOAD="false"
fi

if [[ "$RELOAD" == "true" ]]; then
    echo "Reloading..."
    /usr/local/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -x /var/run/haproxy.sock -sf $(cat /run/haproxy.pid) &
fi
