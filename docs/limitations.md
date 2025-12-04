---
sidebar_position: 23
---

# Limitations and Considerations

## EasyHAProxy will not work with --network=host

:::danger Network Mode Incompatibility
The `--network=host` option **cannot** be used with EasyHAProxy due to its networking requirements.

EasyHAProxy needs to inspect and interact with Docker containers from within the Docker network where it's running. Using the `--network=host` option bypasses Docker networking, preventing EasyHAProxy from accessing and configuring containers effectively.
:::

## Considerations for Multiple Replica Deployments in EasyHAProxy

:::warning Single Replica Deployment Recommended
EasyHAProxy is designed for single replica deployment.
:::

### What happens with multiple replicas?

EasyHAProxy can still operate with multiple replicas; however:

1. **Service Discovery**: Each replica will independently discover services, which may lead to temporary inconsistencies among replicas (out-of-sync for a few seconds).

2. **ACME/Certificate Issues**: Running multiple replicas creates significant problems with Let's Encrypt and other ACME certificate issuance:
   - Each replica will attempt to obtain its own certificate
   - ACME challenges may be directed to different replicas, causing failures
   - You may quickly hit certificate issuance rate limits
   - Certificate renewal may fail unpredictably

:::danger Recommendation
If you need to run multiple replicas for high availability, **do not activate ACME/Let's Encrypt**. Instead, use manually managed certificates or an external certificate management solution.
:::

----
[Open source ByJG](http://opensource.byjg.com)
