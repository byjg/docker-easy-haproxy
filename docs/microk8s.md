# Microk8s Add-ons

Microk8s is a lightweight Kubernetes distribution that can run on a single machine. It is very easy to install and use.
You can add custom addons to your Microk8s installation.

Here are the steps to install EasyHAProxy on your Microk8s.

## Enabling EasyHAProxy on MicroK8s

EasyHAProxy is being part of official MicroK8s Community edition since MicroK8s version 1.27.

Just enable the community add-on

```
microk8s enable community
```

and you'll see:

```
$ microk8s status

microk8s is running
...
addons:
  ...
  disabled:
    easyhaproxy          # (community) EasyHAProxy can detect and configure HAProxy automatically based on ingress labels
```

However, if you are using MicroK8s before 1.27 you need to enable it directly from the ByJG repository by accessing the microk8s host machine and run:

```shell
microk8s addons repo add byjg https://github.com/byjg/microk8s-addons.git
```

And you should see:

```text
$ microk8s status

microk8s is running
...
addons:
  ...
  disabled:
    easyhaproxy          # (byjg) EasyHAProxy can detect and configure HAProxy automatically based on ingress labels
    ....
```

## Installing EasyHAProxy addon

Once you have enable the EasyHAProxy from the community repository or from ByJG repository and can enable it by running:

Usage:

Install as a Daemonset

```shell
microk8s enable easyhaproxy
```

Install as a NodePort

```shell
microk8s enable easyhaproxy --nodeport
```

**Remember**: you need to disable any ingress controller you have previously installed, for example, nginx, traefik, etc. before install EasyHaProxy.

For more parameters you can refer to the [Kubernetes](kubernetes.md) page.

----
[Open source ByJG](http://opensource.byjg.com)
