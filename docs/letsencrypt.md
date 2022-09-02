# Letsencrypt

EasyHAProxy can issue a letsencrypt certificate. Follow the steps below:

Run the EasyHAProxy:

```bash
docker run \
    -e EASYHAPROXY_LETSENCRYPT_EMAIL=john@doe.com
    .... \
    byjg/easy-haproxy
```

Run your container:

```bash
docker run \
    --label easyhaproxy.express.port=80 \
    --label easyhaproxy.express.localport=3000 \
    --label easyhaproxy.express.host=example.org \
    --label easyhaproxy.express.letsencrypt=true \
    .... \
    some/myimage
```

Requirements:

- Your container **must** listen to port 80. Letsencrypt will not issue the certificate if `easyhaproxy.express.port` is in another port, and EasyHAProxy will fail silently.
- You cannot set port 443 for the container with the Letsencrypt because EasyHAProxy will create this port automatically once the certificate is issued.
- `EASYHAPROXY_LETSENCRYPT_EMAIL` environment variable is required to be set. If you don't set it up, EasyHAProxy **will not request** a certificate.

Be aware of Letsencrypt issue limits - https://letsencrypt.org/docs/duplicate-certificate-limit/ and https://letsencrypt.org/docs/rate-limits/

## Persist your Letsencrypt certificates

It is a good idea to store the letsencrypt certificate in persistent storage because of the limit on how many certificates can be issued for the same domain in a period.

To do this, map the folder `/certs/letsencrypt` to a docker volume.

```bash
docker volume create certs_letsencrypt

docker run \
    /* other parameters */
    -v certs_letsencrypt:/certs/letsencrypt \
    -d byjg/easy-haproxy
```

----
[Open source ByJG](http://opensource.byjg.com)
