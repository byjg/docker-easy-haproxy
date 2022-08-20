#!/bin/bash

function log() {
    # ARGS:
    # - loglevel
    # - app
    # - message
    echo [$2] $(date +"$EASYHAPROXY_DATEFORMAT") [$1]: $3
}
