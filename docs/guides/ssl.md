---
sidebar_position: 1
sidebar_label: "Custom SSL Certificates"
---

# Setup custom certificates

You can use your own certificates with EasyHAProxy instead of (or in addition to) automatic ACME/Certbot certificates.

:::info How SSL Termination Works
SSL termination happens at the **HAProxy level**, NOT in your backend containers.

- Your backend containers should **only** expose HTTP (port 80), not HTTPS
- HAProxy handles all SSL/TLS encryption and decryption
- Backend containers receive plain HTTP traffic from HAProxy
- Do NOT configure SSL in your backend application when using EasyHAProxy

This is the **correct design** - it centralizes SSL management at the proxy layer.
:::

:::info Certificate Types
EasyHAProxy supports two certificate sources:
- **ACME/Certbot automatic certificates** - Issued automatically via Let's Encrypt or other ACME providers (see [ACME documentation](./acme.md))
- **Manual/custom certificates** - Your own certificates loaded via volume mount (recommended) or labels (this page)

Both can be used simultaneously. Per domain, ACME certificates (if `certbot=true` label is set) take precedence over manual certificates.
:::

There are two ways to provide custom certificates:

- [Map the certificate as a docker volume](#map-the-certificate-as-a-docker-volume)
- [Setup certificate as a label definition](#setup-certificate-as-a-label-definition-in-docker-container)

## Map the certificate as a docker volume

EasyHAProxy stores the certificates inside the container folder `/etc/easyhaproxy/certs/haproxy`.

1. Run EasyHAProxy with the volume for the certificates:

```bash title="Create and mount certificate volume"
docker volume create certs_haproxy

docker run \
    /* other parameters */
    -v certs_haproxy:/etc/easyhaproxy/certs/haproxy \
    -d byjg/easy-haproxy
```

2. Create a single PEM from the certificate and the key.

```bash title="Combine certificate and key"
cat example.com.crt example.com.key > single.pem

cat single.pem

-----BEGIN CERTIFICATE-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC5ZheHqmBnEJP+
U9r1gxYWKLzdqrMrcxtQN6M1hIH9n0peuJeIrybdcV7sMbStMXI=
-----END CERTIFICATE-----

-----BEGIN PRIVATE KEY-----
MIIEojCCA4qgAwIBAgIUegW2BimwuL4RzRZ2WYkHA6U5nkAwDQYJKoZIhvcNAQEL
3j4wz8/I5fdsk090j4s5KA==
-----END PRIVATE KEY-----
```

3. Copy this certificate to EasyHAProxy volume:

```bash title="Copy certificate to container"
# IMPORTANT: Filename must match the domain!
docker cp single.pem easyhaproxy:/etc/easyhaproxy/certs/haproxy/example.com.pem
```

:::warning Important Notes
- The filename **must match the domain name**: `example.com.pem` for domain `example.com`
- When using volume-mounted certificates, **do NOT** use the `easyhaproxy.[definition].sslcert` label
- The volume mount method and the label method are **mutually exclusive** per domain
- SSL termination happens at HAProxy - your backend containers should only serve HTTP
:::

4. Configure your backend container (no sslcert label needed):

```yaml
services:
  easyhaproxy:
    image: byjg/easy-haproxy:6.0.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - certs_haproxy:/etc/easyhaproxy/certs/haproxy
    ports:
      - "80:80"
      - "443:443"

  myapp:
    image: nginx
    labels:
      easyhaproxy.web.host: example.com
      easyhaproxy.web.port: 80        # Frontend port (HAProxy listens here)
      easyhaproxy.web.localport: 80   # Backend port (your container)
      # NO sslcert label when using volume method!

volumes:
  certs_haproxy:
```

## Setup certificate as a label definition in docker container

:::info Alternative Method
This method embeds certificates directly in container labels. Use it when you want certificates in version control or don't want to manage external files. **Volume method is recommended for most use cases.**
:::

1. Create a single PEM from the certificate and key:

```bash title="Combine certificate and key"
cat example.com.crt example.com.key > single.pem
```

2. Convert the `single.pem` to BASE64 in a single line:

```bash title="Convert to BASE64"
cat single.pem | base64 -w0
```

3. Add the Base64 string to your container label:

```yaml
services:
  myapp:
    image: nginx
    labels:
      easyhaproxy.web.host: example.com
      easyhaproxy.web.port: 80
      easyhaproxy.web.localport: 80
      easyhaproxy.web.sslcert: "LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0t..."  # Base64 certificate
```

:::warning When Using Label Method
- **There is no necessary to** mount the `/etc/easyhaproxy/certs/haproxy` volume for this domain
- Using `sslcert` label means the volume-mounted certificate will be **ignored**
- Certificate is visible in `docker inspect` output (less secure)
- Updating requires container redeployment
:::

----
[Open source ByJG](http://opensource.byjg.com)
