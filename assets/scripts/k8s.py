from kubernetes import client, config
from kubernetes.client.rest import ApiException
import json

# https://github.com/kubernetes-client/python/tree/master/kubernetes/docs

def main():
    config.load_incluster_config()

    api_instance = client.CoreV1Api()
    v1 = client.NetworkingV1Api()
    
    ret = v1.list_ingress_for_all_namespaces(watch=False)

    discover = {}
    for i in ret.items:
        if i.metadata.annotations['kubernetes.io/ingress.class'] != "easyhaproxy-ingress":
            continue

        data = {}
        #ingress_name = i.metadata.name
        data["creation_timestamp"] = i.metadata.creation_timestamp.strftime("%x %X")
        data["resource_version"] = i.metadata.resource_version
        data["namespace"] = i.metadata.namespace
        for rule in i.spec.rules:
            rule_data = {}
            port_number = rule.http.paths[0].backend.service.port.number
            definition = rule.host.replace(".", "-")
            rule_data["easyhaproxy.%s_%s.host" % (definition, port_number)] = rule.host
            rule_data["easyhaproxy.%s_%s.port" % (definition, port_number)] = "80"
            rule_data["easyhaproxy.%s_%s.localport" % (definition, port_number)] = port_number
            service_name = rule.http.paths[0].backend.service.name
            try:
                api_response = api_instance.read_namespaced_service(service_name, i.metadata.namespace)
                cluster_ip = api_response.spec.cluster_ip
            except ApiException as e:
                cluster_ip = None
                # print("Exception when calling CoreV1Api->read_namespaced_service: %s\n" % e)
            
            if cluster_ip is not None:
                if cluster_ip not in discover.keys():
                    discover[cluster_ip] = data
                discover[cluster_ip].update(rule_data)

    for k in discover.keys():
        print("%s=%s" % (k, json.dumps(discover[k])))

if __name__ == '__main__':
    main()

