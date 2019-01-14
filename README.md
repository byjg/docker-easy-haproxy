# Easy HAProxy 

This Docker image will create dynamically the `haproxy.cfg` based on very simple Yaml.

# Features

- Enable or disable Stats on port 1936 with custom password
- Simple mapping host => host:port 
- Simple redirect host => host:port


# Basic Usage

Create a yaml file in your machine called `easyconfig.cfg` and put the contents:

```yaml
stats:
  username: admin
  password: password
  port: 1936         # Optional (default 1936)

customerrors: true   # Optional (default false)

easymapping:
  - port: 80
    hosts:                                     
      host1.com.br: container:5000
      host2.com.br: other:3000
    redirect:
      www.host1.com.br: http://host1.com.br
      
  - port: 443
    ssl_cert: /etc/easyconfig/mycert.pem
    hosts:
      host1.com.br: container:80

  - port: 8080
    hosts:
      host3.com.br: domain:8181
```

Then run (remember to enable the proper ports):

```bash
docker run \ 
    -v /path/to/local:/etc/easyconfig \
    -p 80:80 \
    -p 8080:8080 \
    -p 1936:1936 \
    --name easy-haproxy-instance \
    -d byjg/easy-haproxy
```



# Mapping custom .cfg files

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

# Docker Compose

```yaml
version: "3.4"
services:
  front:
    image: byjg/easy-haproxy
    volume:
      - /path/to/local:/etc/easyconfig
    ports:
      - 80:80
      - 8080:8080
      - 1936:1936
```

# Handling SSL

HaProxy can handle SSL for you. in this case add the parameter pointing to file containing
the pem of certificates and key in only one file:

```
  - port: 443
    ssl_cert: /etc/easyconfig/mycert.pem
    hosts:
      host1.com.br: container:80
```

Important: Different certificates need to be handled in different entries. 

# Setting Custom Errors

Map the volume : `/etc/haproxy/errors-custom/` and put a file named `ERROR_NUMBER.http` where ERROR_NUMBER
is the http error code (e.g. 503.http)  

# Build

```
docker build -t byjg/easy-haproxy .
```

