#!/bin/bash

set -e

# Start k8s-ci before run this command
# docker run --privileged -v /tmp/z:/var/lib/containers -it --rm -v $PWD:/work -w /work byjg/k8s-ci

if [ -z "$DOCKER_USERNAME" ]  || [ -z "$DOCKER_PASSWORD" ] || [ -z "$DOCKER_REGISTRY" ]
then
  echo You need to setup \$DOCKER_USERNAME, \$DOCKER_PASSWORD and \$DOCKER_REGISTRY before run this command.
  exit 1
fi

buildah login --username $DOCKER_USERNAME --password $DOCKER_PASSWORD $DOCKER_REGISTRY

podman run --rm --events-backend=file --cgroup-manager=cgroupfs --privileged docker://multiarch/qemu-user-static --reset -p yes

VERSIONS="latest $TRAVIS_TAG"
for VERSION in $VERSIONS
do
  DOCKERFILE=Dockerfile

  buildah manifest create byjg/easy-haproxy:$VERSION

  buildah bud --arch arm64 --os linux --iidfile /tmp/iid-arm64 -f $DOCKERFILE -t byjg/easy-haproxy:$VERSION-arm64 .
  buildah bud --arch amd64 --os linux --iidfile /tmp/iid-amd64 -f $DOCKERFILE -t byjg/easy-haproxy:$VERSION-amd64 .

  buildah manifest add byjg/easy-haproxy:$VERSION --arch arm64 --os linux --variant v8 $(cat /tmp/iid-arm64)
  buildah manifest add byjg/easy-haproxy:$VERSION --arch amd64 --os linux --os=linux $(cat /tmp/iid-amd64)

  buildah manifest push --all --format v2s2 byjg/easy-haproxy:$VERSION docker://byjg/easy-haproxy:$VERSION
done

