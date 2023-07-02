# SSL - Automatic Certificate Management Environment (ACME)

The Automatic Certificate Management Environment (ACME) protocol 
allow automating interactions between certificate authorities and their users' servers,
allowing the automated deployment of public key infrastructure. 

Most of the issuers offers Automatic Issuing free of cost.

To enable the ACME protocol we need to enable Certbot in EasyHAProxy by setting up to 4 environment variables:

- EASYHAPROXY_CERTBOT_AUTOCONFIG (optional): Will use pre-sets for your Certificate Authority (CA). See table below.
- EASYHAPROXY_CERTBOT_EMAIL (required): Your email in the certificate authority. 
- EASYHAPROXY_CERTBOT_SERVER (optional): The ACME Endpoint of your certificate authority. If you use AUTOCONFIG, it is set automatically. See table below.
- EASYHAPROXY_CERTBOT_EAB_KID (optional): External Account Binding (EAB) Key Identifier (KID) provided by your certificate authority. Some CA require it. See table below. 
- EASYHAPROXY_CERTBOT_EAB_HMAC_KEY (optional): External Account Binding (EAB) HMAC Key provided by your certificate authority. Some CA require it. See table below.

Here are detailed instructions per Certificate Authority (CA). If anyone is missing, please let's know.

| CA                   | Auto Config      | Free? | Account Required?  | EAB KID? | EAB HMAC Key? | More Info                                                                                                                                                          |
|----------------------|------------------|-------|--------------------|----------|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Let's Encrypt        | -                | Yes   | No                 | No       | No            | [Link](letsencrypt.md)                                                                                                                                             |
| Let's Encrypt (Test) | letsencrypt_test | Yes   | No                 | No       | No            | [Link](letsencrypt.md)                                                                                                                                             |
| ZeroSSL              | zerossl          | Yes   | No                 | No       | No            | [Link](https://zerossl.com/documentation/acme/)                                                                                                                    |
| BuyPass              | buypass          | Yes   | No                 | No       | No            | [Link](https://community.buypass.com/t/63d4ay/buypass-go-ssl-endpoints-updated-14-05-2020)                                                                         |
| BuyPass (test)       | buypass_test     | Yes   | No                 | No       | No            | [Link](https://community.buypass.com/t/63d4ay/buypass-go-ssl-endpoints-updated-14-05-2020)                                                                         |
| Google               | google           | Yes   | Yes                | Yes      | Yes           | [Link](https://cloud.google.com/blog/products/identity-security/automate-public-certificate-lifecycle-management-via--acme-client-api)                             |
| Google Test          | google_test      | Yes   | Yes                | Yes      | Yes           | [Link](https://cloud.google.com/blog/products/identity-security/automate-public-certificate-lifecycle-management-via--acme-client-api)                             |
| SSLCOM RCA           | sslcom_rca       | Yes   | No. Keys by email. | Yes      | Yes           | [Link](https://www.ssl.com/blogs/sslcom-supports-acme-protocol-ssl-tls-certificate-automation/)                                                                    |
| SSLCOM ECC           | sslcom_ecc       | Yes   | No. Keys by email. | Yes      | Yes           | [Link](https://www.ssl.com/blogs/sslcom-supports-acme-protocol-ssl-tls-certificate-automation/)                                                                    |
| Digicert             | -                | No    | Yes                | Yes      | Yes           | [Link](https://docs.digicert.com/en/certcentral/certificate-tools/certificate-lifecycle-automation-guides/use-a-third-party-acme-client-for-host-automations.html) |
| Entrust              | -                | No    | Yes                | Yes      | Yes           | [Link](https://www.entrust.com/knowledgebase/ssl/how-to-use-acme-to-install-ssl-tls-certificates-in-entrust-certificate-services-apache)                           |
| Sectigo              | -                | No    | Yes                | Yes      | Yes           | [Link](https://www.sectigo.com/resource-library/sectigos-acme-automation)                                                                                          |

This configuration is global. After set up ACME properly, is necessary enable for each domain the certificate request. 

To do that add the label: `easyhaproxy.<definition>.certbot=true`. See the method of installation you are using to learn how to set up properly.
