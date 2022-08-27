# Setup your own certificates

You can use your certificates with EasyHAProxy. 

There is two ways to do that. 

## Setup certificate as a label definition in docker container

1. First, Create a single PEM from the certificate and the key. 

```bash
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

2. Convert the `single.pem` to BASE64 in a single line:

```bash
cat single.pem | base64 -w0
```

3. Use this string to define the label `easyhaproxy.[definition].sslcert`

## Map the certificate as docker volume

EasyHAProxy stores the certificates inside the folder `/certs/haproxy`.

1. Run EasyHAProxy with the volume for the certificates:

```bash
docker volume create certs_haproxy

docker run \
    /* other parameters */
    -v certs_haproxy:/certs/haproxy \
    -d byjg/easy-haproxy
```

2. Create a single PEM from the certificate and the key.

```bash
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

3. Copy this certificate to EasyHAProxy volume

```bash
docker cp single.pem easyhaproxy:/certs/haproxy
```

----
[Open source ByJG](http://opensource.byjg.com)
