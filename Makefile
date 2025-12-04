VERSION := $(shell git rev-parse --short HEAD)

.PHONY: build
build:
	docker build -t byjg/easy-haproxy --build-arg RELEASE_VERSION_ARG="$(VERSION)" -t byjg/easy-haproxy:local -f build/Dockerfile .

.PHONY: test
test:
	cd src/ && pytest tests/ -vv
