#!/usr/bin/env bash

#docker run \
#    -l com.byjg.easyhaproxy.definitions=http \
#    -l com.byjg.easyhaproxy.port.http=80 \
#    -l com.byjg.easyhaproxy.port.localport=80 \
#    -l com.byjg.easyhaproxy.host.http=byjg.com.br \
#    -l com.byjg.easyhaproxy.redirect.http=byjg.com.br%http://www.byjg.com.br,byjg.com%http://www.byjg.com.br \
#-d byjg/php:7.3-fpm-nginx


touch ./.docker_data ./docker_data_old

mv ./.docker_data ./docker_data_old

CONTAINERS=$(docker node ps $(docker node ls -q) --format "{{ .Name }}" --filter desired-state=running | cut -d. -f1 | sort | uniq)

for container in $CONTAINERS; do
    docker inspect --format "{{ json .Spec.Labels }}" $container | xargs -I % echo $container=% >> ./.docker_data
done


if cmp -s ./.docker_data ./.docker_data_old ; then
   exit 0
fi

python3 swarm.py
# byjg_site={"com.byjg.easyhaproxy.definition":"http","com.byjg.easyhaproxy.host.http":"byjg.com.br","com.byjg.easyhaproxy.port.http":"80","com.byjg.easyhaproxy.redirect.http":"byjg.com.br%http://www.byjg.com.br,byjg.com%http://www.byjg.com.br","maintainer":"Joao Gilberto Magalhaes"}
