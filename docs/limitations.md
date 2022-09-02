# Limitations

EasyHAProxy currently expects to work in a single replica.

If more than one replica is running, EasyHAProxy will continue to work. However, each replica will discover the services independently.

It means replicas can be out-of-sync for a few seconds because each replica will discover the pods separately.

For Letsencrypt, this is worse because each replica will have a Letsencrypt certificate, and issuing a new one can fail because the
letsencrypt challenge can be directed to the other replica. Also, you can hit the certificate issue limit. So if you intend to run multiple replicas **do not** activate letsencrypt.

----
[Open source ByJG](http://opensource.byjg.com)