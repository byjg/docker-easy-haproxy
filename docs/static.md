# Static File

## Setup Docker EasyHAProxy

This method will use a static configuration, which is simpler and easier than creating a `haproxy.cfg`

You can use this configuration to set up external servers unrelated to docker or Kubernetes.

Another advantage is that EasyHAProxy will monitor for changes in this file and automatically reconfigure HAProxy when any changes are detected.

First, Create a YAML:

```yaml
stats:
  username: admin
  password: password
  port: 1936         # Optional (default 1936)

customerrors: true   # Optional (default false)

ssl_mode: default

logLevel:
  haproxy: INFO

certbot: {
  "email": "acme@example.org"
}

easymapping:
  - port: 80
    hosts:
      host1.com.br: 
        containers:
          - container:5000
        certbot: true
        redirect_ssl: true
      host2.com.br: 
        containers:
          - other:3000
    redirect:
      www.host1.com.br: http://host1.com.br

  - port: 443
    hosts:
      host1.com.br: 
        containers:
          - container:80
        redirect_ssl: false
      ssl: true

  - port: 8080
    hosts:
      host3.com.br: 
        containers: 
          - domain:8181
```

Then map this file to `/etc/haproxy/static/config.yml` in your EasyHAProxy container as:

```bash
docker run -d \
      --name easy-haproxy-container \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v /my/static/:/etc/haproxy/static/ \
      -e EASYHAPROXY_DISCOVER="static" \
      # + Environment Variables \
      -p 80:80 \
      -p 443:443 \
      -p 1936:1936 \
      --network easyhaproxy \
    byjg/easy-haproxy
```

You can find other informations on [docker label configuration](container-labels.md) and [environment variable guide](environment-variable.md)

## Yaml Definition

```yaml
stats:
  username: admin     # Optional (default "admin")
  password: password  # If stats or stats.password is omitted, stats will be public with no password
  port: 1936          # Optional (default 1936)

customerrors: true   # Optional (default false)

ssl_mode: default    # Optional

logLevel:
  certbot: DEBUG       # Optional (default: DEBUG). Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  easyhaproxy: DEBUG   # Optional (default: DEBUG). Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL
  haproxy: INFO        # Optional (default: INFO). Can be: TRACE,DEBUG,INFO,WARN,ERROR,FATAL

certbot:       
  email: "acme@example.org"  # If email is defined enable ACME/Certbot
  autoconfig: ""             # If empty use letsencrypt, otherwise try to set the CA defined. 
  eab_hmac_key: ""           # If required by the CA, set here.
  eab_kid: ""                # If required by the CA, set here.
  server: False              # If empty/False uses Letsencrypt, otherwise the CA Endpoint defined here
  retry_count: 60            # If the certificate reaches the Rate Limit, try again after 'n' iterations.
}

easymapping:
  - port: 80                 # Listen port
    mode: http               # Optional. Default `http`. Can be http or tcp
    hosts:
      host1.com.br:          # Hostname
        containers:
          - container:5000   # Endpoints of the hostname above (ip, dns, container, etc)
        certbot: true        # Optional. it will request a certbot certificate. Needs certbot.email set.
        redirect_ssl: true   # Optional. It will redirect this site to it SSL.
        balance: roundrobin  # Optional. Default `roundrobin`. Can be roundrobin, leastconn, source
        plugin:              # Optional. Default `none`.
          - name1: args1
          - name2: args2
    ssl: true                # Optional. Inform this port will listen to SSL, instead of HTTP
    clone_to_ssl: true       # Optional. Default False. You clone these hosts to its equivalent SSL. 
    redirect:
      www.host1.com.br: http://host1.com.br
```

**Note**: The only way to pass SSL certificates in the static configuration file is to map the certificates
to EasyHAProxy as a docker volume. Refer to the [SSL documentation](ssl.md) to learn how to do it. 

----
[Open source ByJG](http://opensource.byjg.com)
