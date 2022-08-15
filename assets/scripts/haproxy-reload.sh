#!/usr/bin/env bash

cd /scripts

RELOAD="true"

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
        CONTAINERS=$(docker ps -q)
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
    fi
fi

if cmp -s ${CONTROL_FILE} ${CONTROL_FILE}.old ; then
    RELOAD="false"
fi

if [[ ! -z "$1" ]]; then
    echo "Initial configuration"
    RELOAD="false"
fi

/scripts/certbot.sh

# If Certbot reloads successfully will create the file /tmp/force-reload
if [ -f /tmp/force-reload ]; then
    RELOAD="true"
    rm /tmp/force-reload
fi

if [[ "$RELOAD" == "true" ]]; then
    echo "Reloading..."
    /usr/sbin/haproxy -W -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -x /var/run/haproxy.sock -sf $(cat /run/haproxy.pid) &
fi
