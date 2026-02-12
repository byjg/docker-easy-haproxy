# Header Echo Server - Test Fixture

A lightweight Python HTTP server that echoes all request headers as JSON. Used for testing HAProxy plugins that manipulate headers and client IPs.

## Purpose

This test fixture is used by both Docker Compose and Kubernetes test suites to verify:
- Header manipulation (e.g., X-Forwarded-For, CF-Connecting-IP)
- IP restoration plugins (Cloudflare, custom CDN integrations)
- Request routing and backend visibility

## Usage

### Docker Compose
```yaml
services:
  webapp:
    build: ../fixtures/header-echo
    ports:
      - "8080:8080"
```

### Kubernetes
```bash
# Build and load into kind cluster
docker build -t header-echo-server:test .
kind load docker-image header-echo-server:test --name your-cluster

# Use in deployment
spec:
  containers:
  - name: webapp
    image: header-echo-server:test
    imagePullPolicy: Never
```

### Manual Testing
```bash
# Start the server
python3 server.py

# Test it
curl http://localhost:8080
# Returns JSON with all headers, client IP, and X-Forwarded-For value
```

## Response Format

```json
{
  "headers": {
    "Host": "localhost:8080",
    "User-Agent": "curl/7.81.0",
    "Accept": "*/*"
  },
  "client_ip": "127.0.0.1",
  "x_forwarded_for": "NOT SET"
}
```

## Used By

- `examples/docker/docker-compose-cloudflare.yml`
- `examples/docker/test_docker_compose.py::TestCloudflare`
- `examples/kubernetes/cloudflare.yml`
- `examples/kubernetes/test_kubernetes.py::TestCloudflare`
