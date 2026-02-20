---
sidebar_position: 6
sidebar_label: "Helm"
---

# Helm 3

Helm is a package manager for Kubernetes. It allows you to install and manage applications on Kubernetes.

## Setup EasyHAProxy with Helm 3

### 1) Install EasyHAProxy

```bash title="Add the Helm repository"
helm repo add byjg https://opensource.byjg.com/helm
helm repo update byjg
kubectl create namespace easyhaproxy
```

```bash title="Install with Helm"
helm upgrade --install ingress byjg/easyhaproxy \
    --namespace easyhaproxy \
    --set resources.requests.cpu=100m \
    --set resources.requests.memory=128Mi
```

### 2) Choose a deployment mode

By default, EasyHAProxy installs as a **DaemonSet** (`service.create: false`). To use the recommended **NodePort** or **ClusterIP** modes instead, set `service.create: true`:

```bash title="NodePort (recommended)"
helm upgrade --install ingress byjg/easyhaproxy \
    --namespace easyhaproxy \
    --set service.create=true \
    --set service.type=NodePort
```

```bash title="ClusterIP (behind LoadBalancer)"
helm upgrade --install ingress byjg/easyhaproxy \
    --namespace easyhaproxy \
    --set service.create=true \
    --set service.type=ClusterIP
```

See [Deployment Modes](../getting-started/kubernetes.md#deployment-modes) for a comparison of all three modes.

For the complete list of configurable values, see the [Helm Values reference](../reference/helm.md).

----
[Open source ByJG](http://opensource.byjg.com)
