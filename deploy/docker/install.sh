#!/bin/bash

ASSETS_DIR="$(dirname "${BASH_SOURCE[0]}")"/../../build/assets/certs/haproxy

docker network create easyhaproxy
docker volume create certs_certbot
docker volume create certs_haproxy

docker run -d --rm --name easyhaproxy_install -v certs_haproxy:/certs alpine tail -f /dev/null
docker cp $ASSETS_DIR/place_holder_cert.pem easyhaproxy_install:/certs/place_holder_cert.pem
docker stop easyhaproxy_install

echo
echo
echo make sure to add to all of your containers:
echo
echo docker-compose
echo ==============
echo "networks:"
echo "   default:"
echo "     name: easyhaproxy"
echo "     external: true"

echo
echo
echo docker run
echo ==============
echo docker run ... --network easyhaproxy ... your_image:tag
echo