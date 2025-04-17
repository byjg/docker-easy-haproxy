# EasyHAProxy

EasyHAProxy is a simple and easy way to automate the creation of HAProxy configuration file based on Docker containers.

The Helm package makes it easy to deploy EasyHAProxy on Kubernetes.

More information about [EasyHAProxy](https://github.com/byjg/docker-easy-haproxy/blob/master/README.md).

## Install

```bash
helm repo add byjg https://opensource.byjg.com/helm
helm repo update byjg
helm upgrade --install --create-namespace -n easyhaproxy easyhaproxy byjg/easyhaproxy
```

## Deployment Types

EasyHAProxy can be deployed in two ways:

1. **DaemonSet (default)**: When `service.create: false`, EasyHAProxy is deployed as a DaemonSet with hostPort, and will only be scheduled on nodes with the masterNode label.
2. **Deployment**: When `service.create: true`, EasyHAProxy is deployed as a Deployment with a Service (ClusterIP or NodePort), and the `replicaCount` value determines the number of replicas (defaults to 1 if not specified).

## Parameters

```yaml
replicaCount: 1  # Only applies when service.create is true (defaults to 1 if not specified)

image:
  repository: byjg/easy-haproxy
  pullPolicy: Always # IfNotPresent
  # Overrides the image tag whose default is the chart appVersion.
  tag: ""

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

service:
  create: false          # If false, it will create a Daemonset with hostPort. The easiest. 
  type: ClusterIP        # or NodePort
  annotations: {}

binding:
  ports:
    http: 80
    https: 443
    stats: 1936
  additionalPorts: []

easyhaproxy:
  stats:
    username: admin
    password: password
  refresh: "10"
  customErrors: "true"
  sslMode: loose
  logLevel:
    certbot: DEBUG
    easyhaproxy: DEBUG
    haproxy: DEBUG
  certbot:
    email: ""

# Master node configuration - only used when service.create is false (DaemonSet mode)
# When service.create is true (Deployment with ClusterIP/NodePort), this is ignored
masterNode:
  label: easyhaproxy/node
  values: 
    - master
```



