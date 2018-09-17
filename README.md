# Easy HAProxy 

This Docker image will create dynamically the `haproxy.cfg` based on the arguments defined in the command line.

## Features

- Enable or disable Stats on port 1936 with custom password
- Add a mapping from a host to another based on Environment Variables
- Dont need to setup .cfg file
- You can add custom .cfg file by mapping the `conf.d` folder


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
    -p 80:80 \
    --name easy-haproxy-instance \
    -d byjg/easy-haproxy
```

## Mapping custom .cfg files

Just create a folder and put files with the extension .cfg. and map the volume to the container. 
This will concatenate your config into the main haproxy.cfg

```bash
docker run \ 
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -d byjg/easy-haproxy
```

Check if your config is ok:

```bash
docker run \ 
    /* other parameters */
    -v /your/local/conf.d:/etc/haproxy/conf.d \
    -byjg/easy-haproxy -c -f /etc/haproxy/haproxy.cfg
```


## Build

```
docker build -t byjg/easy-haproxy .
```
