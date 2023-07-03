# Volumes

You can map the following volumes:

| Volume                      | Description                                                                                                                   |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| /etc/haproxy/static/        | The folder that will contain the [config.yml](static.md) file for static configuration                                        |
| /certs/haproxy/             | The folder that will contain the certificates (`PEM`) for the [SSL](ssl.md)                                                   |
| /certs/certbot/             | The folder that will contain the certificates (`PEM`) processed by Certbot (e.g. Let's Encrypt). More info: [acme](acme.md).  |
| /etc/haproxy/conf.d/        | The folder that will contain the [custom configuration](other.md) files.                                                      |
| /etc/haproxy/errors-custom/ | The folder that will contain the [custom error](other.md) html files.                                                         |

----
[Open source ByJG](http://opensource.byjg.com)
