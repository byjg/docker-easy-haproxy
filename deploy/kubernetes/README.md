# Kubernetes Static Manifests

⚠️ **IMPORTANT**: These files are **auto-generated** from Helm templates. Do not edit them directly!

## About These Files

This directory contains pre-rendered Kubernetes manifests for deploying EasyHAProxy without Helm. These are generated from the Helm chart at `../../helm/easyhaproxy/` and provide three deployment options:

| File                        | Type                   | Use Case                                                     |
|-----------------------------|------------------------|--------------------------------------------------------------|
| `easyhaproxy-daemonset.yml` | DaemonSet + hostPort   | Direct host networking, best for bare-metal or simple setups |
| `easyhaproxy-nodeport.yml`  | Deployment + NodePort  | Exposes via NodePort (31080/31443/31936)                     |
| `easyhaproxy-clusterip.yml` | Deployment + ClusterIP | Internal cluster access only, use with external LoadBalancer |

## How to Use

Choose the manifest that fits your deployment scenario:

```bash
# Option 1: DaemonSet mode (hostPort)
kubectl apply -f easyhaproxy-daemonset.yml

# Option 2: NodePort mode
kubectl apply -f easyhaproxy-nodeport.yml

# Option 3: ClusterIP mode
kubectl apply -f easyhaproxy-clusterip.yml
```

For more details, see the [Kubernetes documentation](../../docs/kubernetes.md).

## Regenerating These Files

**When to regenerate:**
- After modifying Helm chart templates (`helm/easyhaproxy/templates/`)
- After updating default values (`helm/easyhaproxy/values.yaml`)
- After a new release to sync with latest Helm chart

**How to regenerate:**

```bash
# Navigate to helm directory
cd helm

# Generate DaemonSet manifest (hostPort mode)
helm template ingress ./easyhaproxy --namespace easyhaproxy \
  --set service.create=false \
  > ../deploy/kubernetes/easyhaproxy-daemonset.yml

# Generate NodePort manifest
helm template ingress ./easyhaproxy --namespace easyhaproxy \
  --set service.create=true \
  --set service.type=NodePort \
  > ../deploy/kubernetes/easyhaproxy-nodeport.yml

# Generate ClusterIP manifest
helm template ingress ./easyhaproxy --namespace easyhaproxy \
  --set service.create=true \
  --set service.type=ClusterIP \
  > ../deploy/kubernetes/easyhaproxy-clusterip.yml
```

**Verify regeneration:**

```bash
# Check IngressClass is present
grep "kind: IngressClass" ../deploy/kubernetes/easyhaproxy-*.yml

# Validate manifest syntax
kubectl apply --dry-run=client -f ../deploy/kubernetes/easyhaproxy-daemonset.yml
```

## What's Included

Each manifest contains:
- **ServiceAccount**: RBAC identity for EasyHAProxy
- **ClusterRole**: Permissions to read Ingress resources and Secrets
- **ClusterRoleBinding**: Binds the role to the service account
- **IngressClass**: Defines `easyhaproxy` as the ingress class
- **DaemonSet/Deployment**: The EasyHAProxy workload
- **Service** (NodePort/ClusterIP only): Network exposure

## Source of Truth

The Helm chart at `../../helm/easyhaproxy/` is the **source of truth**. All changes should be made there, then these static manifests regenerated.

**To modify these deployments:**
1. Edit Helm templates in `helm/easyhaproxy/templates/`
2. Update default values in `helm/easyhaproxy/values.yaml`
3. Regenerate static manifests using commands above
4. Commit both Helm changes and regenerated manifests