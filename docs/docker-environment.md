# Docker environment variables

| Environment Variable            | Description                                                                                     | Default          |
|---------------------------------|-------------------------------------------------------------------------------------------------|------------------|
| EASYHAPROXY_DISCOVER            | How the services will be discovered to create `haproxy.cfg`:  `static`, `docker`, `swarm` or `kubernetes`     | **required**     |
| EASYHAPROXY_LABEL_PREFIX        | (Optional) The key will search for matching resources.                                          | `easyhaproxy`    |
| EASYHAPROXY_LETSENCRYPT_EMAIL   | (Optional) The email will be used to request the certificate to Letsencrypt                     | *empty*          |
| EASYHAPROXY_LETSENCRYPT_SERVER  | (Optional) Can be `staging` or 'schema://domain.tld'. If set, will try to connect to the Letsencrypt test server  | *empty*            |
| EASYHAPROXY_SSL_MODE            | (Optional) `strict` supports only the most recent TLS version; `default` good SSL integration with recent browsers; `loose` supports all old SSL protocols for old browsers (not recommended).  | `default`|
| EASYHAPROXY_REFRESH_CONF        | (Optional) Check configuration every N seconds.                                                 | 10               |
| EASYHAPROXY_LOG_LEVEL           | (Optional) The log level for EasyHAproxy messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL | DEBUG            |
| CERTBOT_LOG_LEVEL               | (Optional) The log level for Certbot messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL     | DEBUG            |
| HAPROXY_LOG_LEVEL               | (Optional) The log level for HAProxy messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL     | DEBUG            |
| HAPROXY_USERNAME                | (Optional) The HAProxy username to the statistics.                                              |  `admin`         |
| HAPROXY_PASSWORD                | (Optional) The HAProxy password to the statistics. If not set, statistics will be available with no password  | *empty* |
| HAPROXY_STATS_PORT              | (Optional) The HAProxy port to the statistics. If set to `false`, disable statistics            | `1936`           |
| HAPROXY_CUSTOMERRORS            | (Optional) If HAProxy will use custom HTML errors. true/false.                                  | `false`          |



----
[Open source ByJG](http://opensource.byjg.com)
