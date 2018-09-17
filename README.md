# Easy HAProxy 

This Docker image will create dynamically the `haproxy.cfg` based on the arguments defined in the command line.

## Features

- Enable or disable Stats on port 1936 with custom password
- Add a mapping from a host to another

## Usages

The most common use is to use on Docker Swarm environment when you don't want to expose 
the container ports and use a Load Balance to deliver to this component in the same 
overlay network

## Basic Usage

You have to define 3 variables (LB_STATS_USER, LB_STATS_PASS, LB_HOSTS). 

Example:
- HAProxy with statistics and password "mypassowrd" for the user "admin"
- Domain `my.domain.com` routing to container/host `container1` on port 8080
- Domain `other.domain.com` routing to container/host `other` on port 7000


```bash
docker run \ 
    -e LB_STATS_USER=admin \
    -e LB_STATS_PASS=mypassword \
    -e LB_HOSTS="my.domain.com container1:8080 other.domain.com other:7000" \
    --name easy-haproxy-instance \
    -t -d byjg/easy-haproxy
```


## Build

```
docker build -t byjg/easy-haproxy .
```
