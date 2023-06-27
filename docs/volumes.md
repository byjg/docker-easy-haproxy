# Volumes

You can map the following volumes:

|  Volume | Description |
|------|------|
| /etc/haproxy/static/ | The folder that will contain the [config.yml](static.md) file for static configuration |
| /certs/haproxy/ | The folder that will contain the certificates (`PEM`) for the [SSL](ssl.md) |
| /certs/letsencrypt/ | The folder that will contain the certificates (`PEM`) for the SSL. Use this volume to cache the [letsencrypt](letsencrypt.md) certificate and avoid re-issue certificates between restarts. |
| /etc/haproxy/conf.d/ | The folder that will contain the [custom configuration](other.md) files. |
| /etc/haproxy/errors-custom/ | The folder that will contain the [custom error](other.md) files. |

----
[Open source ByJG](http://opensource.byjg.com)