# Kubernetes

## Setup Kubernetes EasyHAProxy

EasyHAProxy is a Daemonset and it will query all ingress definitions with the annotation `kubernetes.io/ingress.class: easyhaproxy-ingress`.

Once find the annotation, it will immediatelly setup HAProxy and start to serve it.

To install the daemonset in your cluster follow these steps:

1. Identify the node where your EasyHAProxy container will run.

EasyHAProxy is a daemonset but it will be limited to a single node. To understand that see [limitations](limitations.md) page.

```bash
$ kubectl get nodes

NAME      STATUS   ROLES    AGE    VERSION
node-01   Ready    <none>   561d   v1.21.13-3
node-02   Ready    <none>   561d   v1.21.13-3
```

2. Add the EasyHAProxy label to the node

```bash
kubectl label nodes node-01 "easyhaproxy/node=master"
```

3. Install EasyHAProxy

There are two ways to install EasyHAProxy in a Kubernetes cluster. You can use Kubernetes Manifest or Helm 3.

3.1. Using Kubernetes Manifest

```bash
kubectl apply -f \
    https://raw.githubusercontent.com/haproxytech/kubernetes-ingress/master/deploy/haproxy-ingress-daemonset.yaml
```

You can configure the behavior of the EasyHAProxy by setup specific environment variables. To get a list of the variables please follow the [docker container environment](docker-environment.md)

3.2. Using HELM 3

Minimal configuration

```bash
helm repo add byjg https://opensource.byjg.com/helm
helm repo update
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

# Make sure to create this
masterNode:
  label: easyhaproxy/node
  values: 
    - master
```

## Running containers

The only requirement is that you have an ingress properly setup and with the annotation `kubernetes.io/ingress.class: easyhaproxy-ingress`.

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

Once the container is running EasyHAProxy will detect automatically and start to redirect all traffic from `example.org:80` to your container.

You don't need to expose any port in your container.

Caveats:

- At this point, the implementation don't support all ingress properties nor wildcard domains.
- The ingress will publish externally only the ports 80 and 443, plus 1936 if stats is enable.
- EasyHAProxy will read all `spec.rules[].host` spec, however it will parse only the first path `spec.rules[].http.paths[0].port.number` for each rule, and ignore the other paths.

## Kubernetes annotations

| annotation                  | Description                                                                             | Default      | Example      |
|-----------------------------|-----------------------------------------------------------------------------------------|--------------|--------------|
| kubernetes.io/ingress.class | (required) Activate EasyHAProxy.                                                        | **required** | easyhaproxy-ingress
| easyhaproxy.redirect_ssl    | (optional) Boolean. Force redirect all endpoints to https.                              | false        | true or false
| easyhaproxy.letsencrypt     | (optional) Boolean. It will request letsencript certificates for the ingresses domains. | false        | true or false
| easyhaproxy.redirect        | (optional) Json. Specific a domain and its destination.                                 | *empty*      | {"domain":"redirect_url"}
| easyhaproxy.mode            | (optional) Set the HTTP mode for that connection.                                       | http         | http or tcp

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

You need to create a secret with your certificate and key, and associate them in your ingress.

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
