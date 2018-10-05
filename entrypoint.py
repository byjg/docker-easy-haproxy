import yaml
import sys

if len(sys.argv) != 2:
    print("You need to pass the easyconfig.cfg path")
    exit(1)


def defaults(custom):
    result = """
defaults
    log global

    timeout connect    3s
    timeout client    10s
    timeout server    10m
"""
    if custom:
        result += """
    errorfile 400 /etc/haproxy/errors-custom/400.http
    errorfile 403 /etc/haproxy/errors-custom/403.http
    errorfile 408 /etc/haproxy/errors-custom/408.http
    errorfile 500 /etc/haproxy/errors-custom/500.http
    errorfile 502 /etc/haproxy/errors-custom/502.http
    errorfile 503 /etc/haproxy/errors-custom/503.http
    errorfile 504 /etc/haproxy/errors-custom/504.http
"""
    result += """
global
    log /dev/log local0
    maxconn 2000
"""
    return result


def stats(map):
    return """
frontend stats
    bind *:{2}
    mode http
    stats enable
    stats hide-version
    stats realm Haproxy\ Statistics
    stats uri /
    stats auth {0}:{1}
#    acl is_proxystats hdr_dom(host) -i some.host.com
#    default_backend srv_stats
#    use_backend srv_stats if is_proxystats
    default_backend srv_stats

backend srv_stats
    mode http
    server Local 127.0.0.1:{2}
""".format(map["username"], map["password"], map["port"] if "port" in map else 1936)


def easymapping(o):
    port = o["port"]
    hosts = o["hosts"] if "hosts" in o else dict()
    redir = o["redirect"] if "redirect" in o else dict()

    result = """
frontend http_in_{0}
    bind *:{0}
    mode http
    
""".format(port)

    for k in redir:
        host = k.replace(".", "_") + "_{}".format(port)
        result += "    acl is_redir_{0} hdr_dom(host) -i {1}\n".format(host, k)
        result += "    use_backend redir_{0} if is_redir_{0}\n\n".format(host)

    for k in hosts:
        host = k.replace(".", "_") + "_{}".format(port)
        result += "    acl is_rule_{0} hdr_dom(host) -i {1}\n".format(host, k)
        result += "    use_backend srv_{0} if is_rule_{0}\n\n".format(host)

    for k in redir:
        host = k.replace(".", "_") + "_{}".format(port)
        result += """
backend redir_{0}
    mode http
    redirect location {1} code 302
""".format(host, redir[k])

    for k in hosts:
        host = k.replace(".", "_") + "_{}".format(port)
        result += """
backend srv_{0}
    balance roundrobin
    mode http
    option forwardfor
    http-request set-header X-Forwarded-Port %[dst_port]""".format(host) + """
    http-request add-header X-Forwarded-Proto https if { ssl_fc }""" + """
    server srv {0} check weight 1
""".format(hosts[k])

    return result


with open(sys.argv[1], 'r') as content_file:
    parsed = yaml.load(content_file.read())

print(defaults(parsed["customerrors"] if "customerrors" in parsed else False))
if "stats" in parsed:
    print(stats(parsed["stats"]))
if "easymapping" in parsed:
    for k in parsed["easymapping"]:
        print(easymapping(k))


