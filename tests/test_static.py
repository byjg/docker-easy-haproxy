import os

from functions import Functions
from processor import ProcessorInterface


def test_processor_static():
    ProcessorInterface.static_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "./fixtures/static.yml")
    static = ProcessorInterface.factory(ProcessorInterface.STATIC)

    # New format: parsed_object is a dict mapping container IPs to their labels
    # Note: 'container' now has labels for BOTH host1.com.br:80 and host1.com.br:443
    parsed_object = {
        'container': {
            'easyhaproxy.host1_com_br_80.host': 'host1.com.br',
            'easyhaproxy.host1_com_br_80.port': '80',
            'easyhaproxy.host1_com_br_80.localport': '5000',
            'easyhaproxy.host1_com_br_80.certbot': 'true',
            'easyhaproxy.host1_com_br_443.host': 'host1.com.br',
            'easyhaproxy.host1_com_br_443.port': '443',
            'easyhaproxy.host1_com_br_443.localport': '80',
            'easyhaproxy.host1_com_br_443.ssl': 'true',
        },
        'other': {
            'easyhaproxy.host2_com_br_80.host': 'host2.com.br',
            'easyhaproxy.host2_com_br_80.port': '80',
            'easyhaproxy.host2_com_br_80.localport': '3000',
        },
        'redirect-www.host1.com.br-80': {
            'easyhaproxy.www_host1_com_br_80.host': 'www.host1.com.br',
            'easyhaproxy.www_host1_com_br_80.port': '80',
            'easyhaproxy.www_host1_com_br_80.redirect': '{"www.host1.com.br": "http://host1.com.br"}',
            'easyhaproxy.www_host1_com_br_80.redirect_only': 'true',
        },
        'domain': {
            'easyhaproxy.host3_com_br_8080.host': 'host3.com.br',
            'easyhaproxy.host3_com_br_8080.port': '8080',
            'easyhaproxy.host3_com_br_8080.localport': '8181',
        },
    }
    hosts = [
        'host1.com.br:443',
        'host1.com.br:80',
        'host2.com.br:80',
        'host3.com.br:8080'
    ]

    assert static.get_certbot_hosts() is None
    assert static.get_parsed_object() == parsed_object
    assert static.get_hosts() is None

    haproxy_cfg = static.get_haproxy_conf()

    assert haproxy_cfg == Functions.load(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "./expected/static.txt"))

    # @todo: Static doesnt populate this fields
    assert static.get_certbot_hosts() == ['host1.com.br']
    assert static.get_parsed_object() == parsed_object
    assert static.get_hosts() == hosts


def test_processor_static_multiple_domains_same_container():
    """Test that multiple domains can point to the same backend container"""
    ProcessorInterface.static_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "./fixtures/static_multi_domain.yml"
    )
    static = ProcessorInterface.factory(ProcessorInterface.STATIC)

    parsed_object = static.get_parsed_object()

    # Should have labels for both host1 and host2 on the same container
    assert 'webapp' in parsed_object
    webapp_labels = parsed_object['webapp']

    # Check both host definitions are present (this is the key test - both should exist!)
    assert 'easyhaproxy.host1_com_80.host' in webapp_labels
    assert 'easyhaproxy.host2_com_80.host' in webapp_labels
    assert webapp_labels['easyhaproxy.host1_com_80.host'] == 'host1.com'
    assert webapp_labels['easyhaproxy.host2_com_80.host'] == 'host2.com'

    # Generate HAProxy config
    haproxy_cfg = static.get_haproxy_conf()

    # Verify both backends are created
    assert 'backend srv_host1_com_80' in haproxy_cfg
    assert 'backend srv_host2_com_80' in haproxy_cfg

    # Both should point to the same container
    assert haproxy_cfg.count('server srv-0 webapp:8080') == 2


def test_processor_static_with_cors():
    """Test that CORS configuration is properly generated when cors_origin is set"""
    ProcessorInterface.static_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "./fixtures/static_cors.yml"
    )
    static = ProcessorInterface.factory(ProcessorInterface.STATIC)

    haproxy_cfg = static.get_haproxy_conf()

    # Verify CORS configuration is present in stats frontend
    assert '# CORS for stats dashboard (only for configured origin)' in haproxy_cfg
    assert 'acl from_ui hdr(Origin) -i http://localhost:3000' in haproxy_cfg
    assert 'acl preflight method OPTIONS' in haproxy_cfg

    # Verify preflight response
    assert 'http-request return status 204' in haproxy_cfg
    assert 'hdr "Access-Control-Allow-Origin"' in haproxy_cfg
    assert 'hdr "Access-Control-Allow-Methods" "GET, OPTIONS"' in haproxy_cfg
    assert 'hdr "Access-Control-Allow-Headers" "Authorization, Content-Type"' in haproxy_cfg
    assert 'if from_ui preflight' in haproxy_cfg

    # Verify actual response headers (no ACL condition in response phase)
    assert 'http-after-response set-header Access-Control-Allow-Origin "http://localhost:3000"' in haproxy_cfg
    assert 'http-after-response set-header Access-Control-Expose-Headers "X-Request-ID"' in haproxy_cfg
    assert 'http-after-response set-header Vary "Origin"' in haproxy_cfg

    # Verify the full config matches expected
    assert haproxy_cfg == Functions.load(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "./expected/static-cors.txt"))

# test_processor_static()
