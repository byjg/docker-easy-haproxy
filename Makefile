.PHONY: build
build:
	docker build -t byjg/easy-haproxy -t byjg/easy-haproxy:local .

.PHONY: test
test:
	pytest tests/
