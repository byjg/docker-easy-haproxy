#!/bin/sh
set -e

## When docker.sock is mounted its GID comes from the host and is unknown at
## build time. Detect it at startup and add the haproxy user to that group so
## Docker/Swarm discovery works without running the whole process as root.
#if [ -S /var/run/docker.sock ]; then
#    SOCK_GID=$(stat -c '%g' /var/run/docker.sock)
#    getent group "$SOCK_GID" >/dev/null 2>&1 || addgroup -g "$SOCK_GID" dockersock
#    addgroup haproxy "$(getent group "$SOCK_GID" | cut -d: -f1)" 2>/dev/null || true
#fi

exec /scripts/.venv/bin/easy-haproxy "$@"