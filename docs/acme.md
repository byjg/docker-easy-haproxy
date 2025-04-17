# SSL - Automatic Certificate Management Environment (ACME)

The Automatic Certificate Management Environment (ACME) protocol 
allow automating interactions between certificate authorities and their users' servers,
allowing the automated deployment of public key infrastructure. 

Most of the issuers offers Automatic Issuing free of cost.

## Environment Variables

To enable the ACME protocol we need to enable Certbot in EasyHAProxy by setting up to the following environment variables:

| Environment Variable                     | Required? | Description                                                                                                                      |
|------------------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------------------|
| EASYHAPROXY_CERTBOT_EMAIL                | YES       | Your email in the certificate authority.                                                                                         |
| EASYHAPROXY_CERTBOT_AUTOCONFIG           | -         | Will use pre-sets for your Certificate Authority (CA). See table below.                                                          |
| EASYHAPROXY_CERTBOT_SERVER               | -         | The ACME Endpoint of your certificate authority. If you use AUTOCONFIG, it is set automatically. See table below.                |
| EASYHAPROXY_CERTBOT_EAB_KID              | -         | External Account Binding (EAB) Key Identifier (KID) provided by your certificate authority. Some CA require it. See table below. |
| EASYHAPROXY_CERTBOT_EAB_HMAC_KEY         | -         | External Account Binding (EAB) HMAC Key provided by your certificate authority. Some CA require it. See table below.             |
| EASYHAPROXY_CERTBOT_RETRY_COUNT          | -         | Wait 'n' requests before retrying issue invalid requests. Default 60.                                                            |
| EASYHAPROXY_CERTBOT_PREFERRED_CHALLENGES | -         | The preferred challenges for Certbot. Available: `http`                                                                          |
| EASYHAPROXY_CERTBOT_MANUAL_AUTH_HOOK     | -         | The path to a script that will be executed (default: None)                                                                       |

## Auto Config Certificate Authority (CA)

Here are detailed instructions per Certificate Authority (CA). If anyone is missing, please let's know.

Possible values for: `EASYHAPROXY_CERTBOT_AUTOCONFIG`

| CA                   | Auto Config      | Free? | Account Required?  | EAB KID? | EAB HMAC Key? | More Info                                                                                                                                                          |
|----------------------|------------------|-------|--------------------|----------|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Let's Encrypt        | -                | Yes   | No                 | No       | No            | -                                                                                                                                                                  |
| Let's Encrypt (Test) | letsencrypt_test | Yes   | No                 | No       | No            | -                                                                                                                                                                  |
| ZeroSSL              | zerossl          | Yes   | No                 | No       | No            | [Link](https://zerossl.com/documentation/acme/)                                                                                                                    |
| BuyPass              | buypass          | Yes   | No                 | No       | No            | [Link](https://community.buypass.com/t/63d4ay/buypass-go-ssl-endpoints-updated-14-05-2020)                                                                         |
| BuyPass (test)       | buypass_test     | Yes   | No                 | No       | No            | [Link](https://community.buypass.com/t/63d4ay/buypass-go-ssl-endpoints-updated-14-05-2020)                                                                         |
| Google               | google           | Yes   | Yes                | Yes      | Yes           | [Link](https://cloud.google.com/blog/products/identity-security/automate-public-certificate-lifecycle-management-via--acme-client-api)                             |
| Google Test          | google_test      | Yes   | Yes                | Yes      | Yes           | [Link](https://cloud.google.com/blog/products/identity-security/automate-public-certificate-lifecycle-management-via--acme-client-api)                             |
| SSLCOM RCA           | sslcom_rca       | Trial | EAB Keys by email. | Yes      | Yes           | [Link](https://www.ssl.com/blogs/sslcom-supports-acme-protocol-ssl-tls-certificate-automation/)                                                                    |
| SSLCOM ECC           | sslcom_ecc       | Trial | EAB Keys by email. | Yes      | Yes           | [Link](https://www.ssl.com/blogs/sslcom-supports-acme-protocol-ssl-tls-certificate-automation/)                                                                    |
| Digicert             | -                | No    | Yes                | Yes      | Yes           | [Link](https://docs.digicert.com/en/certcentral/certificate-tools/certificate-lifecycle-automation-guides/use-a-third-party-acme-client-for-host-automations.html) |
| Entrust              | -                | No    | Yes                | Yes      | Yes           | [Link](https://www.entrust.com/knowledgebase/ssl/how-to-use-acme-to-install-ssl-tls-certificates-in-entrust-certificate-services-apache)                           |
| Sectigo              | -                | No    | Yes                | Yes      | Yes           | [Link](https://www.sectigo.com/resource-library/sectigos-acme-automation)                                                                                          |

This configuration is global. After set up ACME properly, is necessary enable for each domain the certificate request. 

To do that add the label: `easyhaproxy.<definition>.certbot=true`. See the method of installation you are using to learn how to set up properly.

## Example

### Setting up EasyHAProxy

Run the EasyHAProxy container:

```bash
docker run \
    ... \
    -e EASYHAPROXY_CERTBOT_AUTOCONFIG=zerossl \
    -e EASYHAPROXY_CERTBOT_EMAIL=john@doe.com \
    -p 80:80 \
    -p 443:443 \
    -v /path/to/guest/certbot/certs:/certs/certbot \
    ... \
    byjg/easy-haproxy
```

Notes:

- The `EASYHAPROXY_CERTBOT_AUTOCONFIG` is not required for Let's Encrypt. In this example, the certificate will be issued by ZeroSSL.
- If you don't setup `EASYHAPROXY_CERTBOT_EMAIL` environment variable, EasyHAProxy will fail silently and **will not request** a certificate.
- The ports 80 and 443 needs to accessible through the internet as [Let's Encrypt requirement](https://letsencrypt.org/docs/allow-port-80/)

In order to avoid several certificate issuing, 
**It is required you to persist the container folder `/certs/certbot` outside the container.**
You cannot delete or change it contents. 
If you do not persist, or change/delete the contents, Issue a certificate might not work properly and hit rate limit. 

If you are using Let's Encrypt, be aware of it rate limits:
 
- https://letsencrypt.org/docs/duplicate-certificate-limit/
- https://letsencrypt.org/docs/rate-limits/


## Setting up your container to use the ACME CA

```bash
docker run \
    ... \
    --label easyhaproxy.express.port=80 \
    --label easyhaproxy.express.localport=3000 \
    --label easyhaproxy.express.host=example.org \
    --label easyhaproxy.express.certbot=true \
    ... \
    some/myimage
```

Requirements:

- Your container **must** listen to port 80. The CA will not issue the certificate if `easyhaproxy.<definition>.port` is in another port, and EasyHAProxy will fail silently.
- You cannot set port 443 for the container with the Letsencrypt because EasyHAProxy will create this port automatically once the certificate is issued.

----
[Open source ByJG](http://opensource.byjg.com)