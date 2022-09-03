# Kubernetes

## Setup Kubernetes EasyHAProxy

EasyHAProxy for Kubernetes queries all ingress definitions with the annotation `kubernetes.io/ingress.class: easyhaproxy-ingress`. Once find the annotation, it will immediately set up HAProxy and start to serve it.

There are three installation modes:

- DaemonSet: It will expose ports 80, 443 and 1936
- NodePort: It will expose the ports 31080, 31443 and 31936
- ClusterIP: it will node expose any port. The HAProxy will be accessible only inside the cluster.

To install EasyHAProxy in your cluster, follow these steps:

### 1) Identify the node where your EasyHAProxy container will run.

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

You can install EasyHAProxy in a Kubernetes cluster using Kubernetes Manifest or Helm 3.

#### 2.1.) Using Kubernetes Manifest

```bash
kubectl create namespace easyhaproxy

kubectl apply -f \
    https://raw.githubusercontent.com/byjg/docker-easy-haproxy/4.2.0/deploy/kubernetes/easyhaproxy-daemonset.yml
```

If necessary, you can configure environment variables. To get a list of the variables, please follow the [docker container environment](docker-environment.md)

#### 2.2) Using HELM 3

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
  letsencrypt:
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

## Running containers

Your container only requires creating an ingress with the annotation `kubernetes.io/ingress.class: easyhaproxy-ingress` pointing to your service.

e.g.

```yaml
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: example-ingress
  namespace: example
spec:
  rules:
  - host: example.org
    http:
      paths:
      - backend:
          service:
            name: example-service
            port:
              number: 8080
        pathType: ImplementationSpecific
```

Once the container is running, EasyHAProxy will detect automatically and start to redirect all traffic from `example.org:80` to your container at port 8080.

You don't need to expose any port in your container.

Caveats:

- At this point, the implementation doesn't support all ingress properties or wildcard domains.
- The ingress will publish the ports 80 and 443, plus 1936 if stats are enabled.
- EasyHAProxy will read all `spec.rules[].host` spec, however it will parse only the first path `spec.rules[].http.paths[0].port.number` for each rule, and ignore the other paths.

## Kubernetes annotations

| annotation                  | Description                                                                             | Default      | Example      |
|-----------------------------|-----------------------------------------------------------------------------------------|--------------|--------------|
| kubernetes.io/ingress.class | (required) Activate EasyHAProxy.                                                        | **required** | easyhaproxy-ingress
| easyhaproxy.redirect_ssl    | (optional) Boolean. Force redirect all endpoints to HTTPS.                              | false        | true or false
| easyhaproxy.letsencrypt     | (optional) Boolean. It will request letsencrypt certificates for the ingresses domains. | false        | true or false
| easyhaproxy.redirect        | (optional) JSON. Key pair with a domain and its destination.                                 | *empty*      | {"domain":"redirect_url"}
| easyhaproxy.mode            | (optional) Set the HTTP mode for that connection.                                       | http         | http or tcp
| easyhaproxy.listen_port     | (optional) Set the an additional port for that ingress                                  | http         | http or tcp

**Important**: The annotations are per ingress and applied to all hosts in that ingress configuration.

## Letsencrypt

It is necessary add the annotation `easyhaproxy.letsencrypt` to the ingress configuration:

```yaml
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
    easyhaproxy.letsencrypt: 'true'
  name: example-ingress
  namespace: example
spec:
  ....
```

Make sure your cluster is accessible both through ports 80 and 443.

## Custom SSL Certificates

Create a secret with your certificate and key and associate them with your ingress.

```yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: host2-tls
  namespace: default
data:
  tls.crt: base64 of your certificate
  tls.key: base64 of your certificate private key
type: kubernetes.io/tls

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: easyhaproxy-ingress
  name: tls-example
  namespace: default
spec:
  tls:
  - hosts:
      - host2.local
    secretName: host2-tls
  rules:
    ...
```

----
[Open source ByJG](http://opensource.byjg.com)
