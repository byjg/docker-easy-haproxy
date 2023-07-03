# Helm 3

Helm is a package manager for Kubernetes. It allows you to install and manage applications on Kubernetes.

## Setup EasyHAProxy with Helm 3

### 1) Identify the node where your EasyHAProxy container will run

EasyHAProxy will be limited to a single node. To understand that see [limitations](limitations.md) page.

```bash
$ kubectl get nodes

NAME      STATUS   ROLES    AGE    VERSION
node-01   Ready    <none>   561d   v1.21.13-3
node-02   Ready    <none>   561d   v1.21.13-3
```

Add the EasyHAProxy label to the node.

```bash
kubectl label nodes node-01 "easyhaproxy/node=master"
```

### 2) Install EasyHAProxy

Minimal configuration

```bash
helm repo add byjg https://opensource.byjg.com/helm
helm repo update byjg
kubectl create namespace easyhaproxy

helm upgrade --install ingress byjg/easyhaproxy \
    --namespace easyhaproxy \
    --set resources.requests.cpu=100m \
    --set resources.requests.memory=128Mi
```

Customizing Helm Values:

```yaml
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

service:
  create: false          # If false, it will create a DaemonSet with hostPort. The easiest. 
  type: ClusterIP        # or NodePort
  annotations: {}

binding:
  ports:
    http: 80
    https: 443
    stats: 1936
  additionalPorts: []

# Make sure to create this
masterNode:
  label: easyhaproxy/node
  values: 
    - master
```

For more parameters you can refer to the [Kubernetes](kubernetes.md) page.

----
[Open source ByJG](http://opensource.byjg.com)
