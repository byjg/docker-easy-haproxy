VERSION := $(shell git rev-parse --short HEAD)

.PHONY: build
build:
	docker build -t byjg/easy-haproxy --build-arg RELEASE_VERSION_ARG="$(VERSION)" -t byjg/easy-haproxy:local .

.PHONY: test
test:
	pytest tests/
