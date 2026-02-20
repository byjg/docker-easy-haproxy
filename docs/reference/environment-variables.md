---
sidebar_position: 2
sidebar_label: "Environment Variables"
---

# Docker environment variables

| Environment Variable      | Description                                                                                                                                                                                    | Default            |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|
| EASYHAPROXY_DISCOVER      | How the services will be discovered to create `haproxy.cfg`:  `static`, `docker`, `swarm` or `kubernetes`                                                                                      | **required**       |
| EASYHAPROXY_LABEL_PREFIX  | (Optional) The key will search for matching resources.                                                                                                                                         | `easyhaproxy`      |
| EASYHAPROXY_BASE_PATH     | (Optional) Base directory for all EasyHAProxy files. All paths (config, certs, plugins, www) are constructed relative to this base.                                                            | `/etc/easyhaproxy` |
| EASYHAPROXY_CERTBOT_*     | (Optional) Enable Let's Encrypt or any other ACME certificate. See more: [acme](../guides/acme.md)                                                                                             | *empty*            |
| EASYHAPROXY_SSL_MODE      | (Optional) `strict` supports only the most recent TLS version; `default` good SSL integration with recent browsers; `loose` supports all old SSL protocols for old browsers (not recommended). | `default`          |
| EASYHAPROXY_REFRESH_CONF  | (Optional) Check for new containers/services every N seconds.                                                                                                                                  | 10                 |
| EASYHAPROXY_LOG_LEVEL     | (Optional) The log level for EasyHAproxy messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL                                                                                                | DEBUG              |
| CERTBOT_LOG_LEVEL         | (Optional) The log level for Certbot messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL                                                                                                    | DEBUG              |
| HAPROXY_LOG_LEVEL         | (Optional) The log level for HAProxy messages. Available: TRACE,DEBUG,INFO,WARN,ERROR,FATAL                                                                                                    | INFO               |
| HAPROXY_USERNAME          | (Optional) The HAProxy username for the statistics endpoint (used only when `HAPROXY_PASSWORD` is set).                                                                                        | `admin`            |
| HAPROXY_PASSWORD          | (Optional) The HAProxy password to the statistics endpoint. Stats are **disabled** unless this is defined.                                                                                     | *empty*            |
| HAPROXY_STATS_PORT        | (Optional) The HAProxy port to the statistics. If set to `false`, disable statistics. Only applies when `HAPROXY_PASSWORD` is defined.                                                         | `1936`             |
| HAPROXY_STATS_CORS_ORIGIN | (Optional) Enable CORS for the HAProxy stats dashboard by specifying the allowed origin (e.g., `http://localhost:3000`). Only applies when `HAPROXY_PASSWORD` is defined.                      | *empty*            |
| HAPROXY_CUSTOMERRORS      | (Optional) If HAProxy will use custom HTML errors. true/false.                                                                                                                                 | `false`            |

:::tip HAProxy Stats
Statistics are only configured when `HAPROXY_PASSWORD` is set. Without a password, the stats section is not generated.
:::

:::note ACME/Certbot Environment Variables
For ACME/Certbot configuration (Let's Encrypt, ZeroSSL, etc.), see the [ACME documentation](../guides/acme.md#environment-variables) for the complete list of `EASYHAPROXY_CERTBOT_*` variables.
:::

## Kubernetes

These variables apply only when `EASYHAPROXY_DISCOVER=kubernetes`. They control how EasyHAProxy updates Ingress resources with load-balancer IP information.

| Environment Variable               | Description                                                                                                                          | Default |
|------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|---------|
| EASYHAPROXY_UPDATE_INGRESS_STATUS  | Update Ingress resources with the load-balancer IP. Set to `false` to disable.                                                       | `true`  |
| EASYHAPROXY_DEPLOYMENT_MODE        | How to detect and report Ingress IPs: `auto`, `daemonset`, `nodeport`, or `clusterip`. `auto` inspects pod owner references and service type automatically. | `auto`  |
| EASYHAPROXY_EXTERNAL_HOSTNAME      | Hostname to report in Ingress status when using ClusterIP mode without a cloud LoadBalancer.                                          | *(none)* |
| EASYHAPROXY_STATUS_UPDATE_INTERVAL | Seconds between Ingress status update cycles.                                                                                         | `30`    |

:::tip Deployment mode auto-detection
`EASYHAPROXY_DEPLOYMENT_MODE=auto` is recommended. EasyHAProxy inspects its own pod owner references (DaemonSet vs Deployment) and Service type (NodePort vs ClusterIP) to determine the correct IP source. Override only if auto-detection gives wrong results.
:::

----
[Open source ByJG](http://opensource.byjg.com)
