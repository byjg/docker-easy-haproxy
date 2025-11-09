---
sidebar_position: 15
---

# Limitations and Considerations

## EasyHAProxy will not work with --network=host

The --network=host option cannot be used with EasyHAProxy due to its networking requirements. 
EasyHAProxy needs to inspect and interact with Docker containers from within the Docker network 
where it's running. Using the --network=host option bypasses Docker networking, 
preventing EasyHAProxy from accessing and configuring containers effectively.

## Considerations for Multiple Replica Deployments in EasyHAProxy

EasyHAProxy currently operates under the assumption of a single replica deployment.

In the event of multiple replicas, EasyHAProxy can still operate; however, each replica will independently 
discover services. This may lead to temporary inconsistencies among replicas as they may be out-of-sync 
for a few seconds due to separate service discovery processes.

However, it's crucial to highlight that running multiple replicas of EasyHAProxy can significantly 
impact Letsencrypt certificate issuance. Each replica will possess its own Letsencrypt certificate, 
potentially leading to challenges with certificate issuance. Challenges may be directed to different replicas,
leading to potential failures in issuing new certificates and encountering certificate issuance limits. 
Therefore, if you intend to run multiple replicas, it's advised to avoid activating Letsencrypt to mitigate 
these issues.

----
[Open source ByJG](http://opensource.byjg.com)