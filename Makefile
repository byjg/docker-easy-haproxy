VERSION := $(shell git rev-parse --short HEAD)

.PHONY: build
build:
	docker build -t byjg/easy-haproxy --build-arg RELEASE_VERSION_ARG="$(VERSION)" -t byjg/easy-haproxy:local -f build/Dockerfile .

.PHONY: test
test:
	uv run pytest tests/ -vv

.PHONY: sync
sync:
	uv sync --dev

.PHONY: lint
lint:
	uv run ruff check src/ tests/

.PHONY: format
format:
	uv run ruff format src/ tests/
