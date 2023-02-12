# Microk8s Add-ons

Microk8s is a lightweight Kubernetes distribution that can run on a single machine. It is very easy to install and use.
You can add custom addons to your Microk8s installation.
Here are the steps to install EasyHAProxy on your Microk8s.

## Installing ByJG repository

Before install the addons, you need to add the ByJG repository to your Microk8s installation.

1. Access the microk8s host machine and run:

```shell
microk8s addons repo add byjg https://github.com/byjg/microk8s-addons.git
```

2. Check if it is installed:

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

EasyHAProxy can detect and configure HAProxy automatically based on ingress labels.

Usage:

Install as a Daemonset

```shell
microk8s enable easyhaproxy
```

Install as a NodePort

```shell
microk8s enable easyhaproxy --nodeport
```

For more parameters you can refer to the [Kubernetes](kubernetes.md) page.

----
[Open source ByJG](http://opensource.byjg.com)
