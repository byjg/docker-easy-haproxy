---
sidebar_position: 6
sidebar_label: "Helm Values"
---

# Helm Values Reference

Complete reference for all configurable values in the `byjg/easyhaproxy` Helm chart.

## Image Configuration

| Value | Description | Default |
|---|---|---|
| `image.repository` | Container image repository | `byjg/easy-haproxy` |
| `image.tag` | Image tag. Defaults to the chart `appVersion`. | `""` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `imagePullSecrets` | List of image pull secret names | `[]` |
| `nameOverride` | Override the chart name | `""` |
| `fullnameOverride` | Override the full release name | `""` |

## Deployment Mode

Controls whether EasyHAProxy runs as a **Deployment** (with a Service) or a **DaemonSet** (binding to host ports).

| Value | Description | Default |
|---|---|---|
| `replicaCount` | Number of replicas (only used when `service.create: true`) | `1` |
| `service.create` | `true` → Deployment + Service (NodePort or ClusterIP). `false` → DaemonSet with host ports. | `false` |
| `service.type` | Service type when `service.create: true`: `NodePort` or `ClusterIP` | `ClusterIP` |
| `service.annotations` | Annotations to add to the Service resource | `{}` |

:::tip Recommended mode
Set `service.create: true` and `service.type: NodePort` for most setups. DaemonSet mode (`service.create: false`) requires maintaining a node label across node replacements, which can cause outages if forgotten.
:::

## Port Binding

| Value | Description | Default |
|---|---|---|
| `binding.ports.http` | HTTP port | `80` |
| `binding.ports.https` | HTTPS port | `443` |
| `binding.ports.stats` | HAProxy stats port | `1936` |
| `binding.additionalPorts` | List of additional ports to expose | `[]` |

## EasyHAProxy Settings

| Value | Description | Default |
|---|---|---|
| `easyhaproxy.stats.username` | HAProxy stats dashboard username | `admin` |
| `easyhaproxy.stats.password` | HAProxy stats dashboard password | `password` |
| `easyhaproxy.refresh` | Seconds between service discovery polls | `"10"` |
| `easyhaproxy.customErrors` | Enable custom HTML error pages | `"true"` |
| `easyhaproxy.sslMode` | TLS mode: `strict`, `default`, or `loose` | `loose` |
| `easyhaproxy.logLevel.certbot` | Log level for Certbot | `DEBUG` |
| `easyhaproxy.logLevel.easyhaproxy` | Log level for EasyHAProxy | `DEBUG` |
| `easyhaproxy.logLevel.haproxy` | Log level for HAProxy | `DEBUG` |
| `easyhaproxy.certbot.email` | Email address for Let's Encrypt / ACME registration | `""` |

## Ingress Status

Controls how EasyHAProxy updates Kubernetes Ingress resources with load-balancer IPs.

| Value | Description | Default |
|---|---|---|
| `ingressStatus.enabled` | Update Ingress resources with load-balancer IPs | `true` |
| `ingressStatus.deploymentMode` | How to detect/report IPs: `auto`, `daemonset`, `nodeport`, or `clusterip`. `auto` is recommended. | `auto` |
| `ingressStatus.externalHostname` | Hostname to report in Ingress status (for ClusterIP mode without a LoadBalancer) | `""` |
| `ingressStatus.updateInterval` | Seconds between Ingress status updates | `30` |

## DaemonSet Node Selection

:::note Only applies when `service.create: false`
These values are ignored when running as a Deployment (`service.create: true`).
:::

| Value | Description | Default |
|---|---|---|
| `masterNode.label` | Node label key used for `nodeAffinity` | `easyhaproxy/node` |
| `masterNode.values` | Accepted values for the node label | `["master"]` |

Label the target node before installing:

```bash
kubectl label nodes node-01 "easyhaproxy/node=master"
```

## Standard Kubernetes Fields

| Value | Description | Default |
|---|---|---|
| `podAnnotations` | Annotations added to the EasyHAProxy pod | `{}` |
| `resources` | CPU/memory requests and limits for the pod | `{}` |
| `nodeSelector` | Node selector for pod scheduling | `{}` |
| `tolerations` | Tolerations for pod scheduling | `[]` |
| `affinity` | Affinity rules for pod scheduling | `{}` |
| `podSecurityContext` | Pod-level security context | `{}` |
| `securityContext` | Container-level security context | `{}` |

## Service Account

| Value | Description | Default |
|---|---|---|
| `serviceAccount.create` | Create a dedicated ServiceAccount | `true` |
| `serviceAccount.annotations` | Annotations to add to the ServiceAccount | `{}` |
| `serviceAccount.name` | Name of the ServiceAccount. Auto-generated if empty. | `""` |

## Ingress Class

| Value | Description | Default |
|---|---|---|
| `ingressClass.create` | Create an `IngressClass` resource named `easyhaproxy` | `true` |
| `ingressClass.annotations` | Annotations to add to the IngressClass | `{}` |

----
[Open source ByJG](http://opensource.byjg.com)
