# Letsencrypt

EasyHAProxy can issue a letsencrypt certificate. The command is as below:

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
    -l easyhaproxy.express.port=80 \
    -l easyhaproxy.express.localport=3000 \
    -l easyhaproxy.express.host=example.org \
    -l easyhaproxy.express.letsencrypt=true \
    .... \
    some/myimage
```

Requirements:

- Your container **must** listen to the port 80. Besides no error, the certificate won't be issued if in a different port.
- You cannot set the port 443 for the container with the Letsencrypt because EasyHAProxy will handle this automatically once the certificate is issued.
- You have to setup the `EASYHAPROXY_LETSENCRYPT_EMAIL` environment variable on EasyHAProxy. If you don't setup, EasyHAProxy **will not request** a certificate.

Be aware of Letsencrypt issue limits - https://letsencrypt.org/docs/duplicate-certificate-limit/ and https://letsencrypt.org/docs/rate-limits/

## Persist your Letsencrypt certificates

It is a good idea to store the letsencrypt certificate in a persistent storage, even you knowing you can issue again in case your lost the certificate. 

However, there is a limit in how many certificates can be issue for the same domain in a period of time.

To avoid this, map the folder `/certs/letsencrypt` to a docker volume.

```bash
docker volume create certs_letsencrypt

docker run \
    /* other parameters */
    -v certs_letsencrypt:/certs/letsencrypt \
    -d byjg/easy-haproxy
```

----
[Open source ByJG](http://opensource.byjg.com)
