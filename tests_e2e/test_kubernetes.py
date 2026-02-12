"""
Kubernetes Integration Tests for EasyHAProxy

This test suite validates EasyHAProxy Kubernetes examples using kind (Kubernetes IN Docker).

Requirements:
- kind (Kubernetes IN Docker) installed locally in .kind/
- kubectl installed
- Docker running
- PyJWT and cryptography libraries (for JWT tests): pip install pyjwt cryptography

Usage:
    pytest test_kubernetes.py -v
    pytest test_kubernetes.py::TestBasicService -v
    pytest test_kubernetes.py::TestJWTValidatorSecret -v
"""

import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Generator
import urllib.request
import pytest
import requests
from utils import generate_jwt_token, wait_for_pods_ready, create_tls_secret_from_pem, extract_backend_block

# Import JWT libraries for token generation
try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


# Base directory for Kubernetes manifests
BASE_DIR = Path(__file__).parent.absolute()
BIN_DIR = BASE_DIR / "kubernetes" / ".kind"
KIND_BIN = BIN_DIR / "kind"
KUBECTL_BIN = BIN_DIR / "kubectl"
HELM_BIN = BIN_DIR / "helm"

# Port configuration for kind cluster
# These ports map from localhost to the kind cluster
HTTP_PORT = 10080        # HTTP traffic (localhost:10080 -> cluster:80)
HTTPS_PORT = 10443       # HTTPS traffic (localhost:10443 -> cluster:443)
STATS_PORT = 11936       # HAProxy stats (localhost:11936 -> cluster:1936)


# =============================================================================
# Helper Functions
# =============================================================================
def get_latest_kind_version():
    url = "https://api.github.com/repos/kubernetes-sigs/kind/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["tag_name"]  # e.g. "v0.27.0"

def get_latest_helm_version():
    url = "https://api.github.com/repos/helm/helm/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["tag_name"]  # e.g. "v3.17.3"

def ensure_kind_installed():
    """Ensure kind is installed locally in .kind/"""
    if KIND_BIN.exists():
        return str(KIND_BIN)

    print("Installing kind locally...")
    BIN_DIR.mkdir(exist_ok=True)

    # Download kind
    version = get_latest_kind_version()
    subprocess.run(
        ["curl", "-Lo", str(KIND_BIN),
         f"https://kind.sigs.k8s.io/dl/{version}/kind-linux-amd64"],
        check=True,
        capture_output=True
    )

    # Make executable
    KIND_BIN.chmod(0o755)

    print(f"✓ kind {version} installed to {KIND_BIN}")
    return str(KIND_BIN)


def ensure_kubectl_installed():
    """Ensure kubectl is installed locally in .kind/"""
    # Check if kubectl exists globally first
    try:
        subprocess.run(
            ["kubectl", "version", "--client"],
            check=True,
            capture_output=True,
            timeout=5
        )
        return "kubectl"  # Use global kubectl
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Use local kubectl if it exists
    if KUBECTL_BIN.exists():
        return str(KUBECTL_BIN)

    print("Installing kubectl locally...")
    BIN_DIR.mkdir(exist_ok=True)

    # Get latest stable version
    result = subprocess.run(
        ["curl", "-L", "-s", "https://dl.k8s.io/release/stable.txt"],
        check=True,
        capture_output=True,
        text=True
    )
    version = result.stdout.strip()

    # Download kubectl
    subprocess.run(
        ["curl", "-Lo", str(KUBECTL_BIN),
         f"https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl"],
        check=True,
        capture_output=True
    )

    # Make executable
    KUBECTL_BIN.chmod(0o755)

    print(f"✓ kubectl {version} installed to {KUBECTL_BIN}")
    return str(KUBECTL_BIN)


def ensure_helm_installed():
    """Ensure helm is installed locally in .kind/"""
    # Check if helm exists globally first
    try:
        subprocess.run(
            ["helm", "version"],
            check=True,
            capture_output=True,
            timeout=5
        )
        return "helm"  # Use global helm
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Use local helm if it exists
    if HELM_BIN.exists():
        return str(HELM_BIN)

    print("Installing helm locally...")
    BIN_DIR.mkdir(exist_ok=True)

    # Download and extract helm
    helm_version = get_latest_helm_version()
    helm_tar = BIN_DIR / "helm.tar.gz"

    subprocess.run(
        ["curl", "-Lo", str(helm_tar),
         f"https://get.helm.sh/helm-{helm_version}-linux-amd64.tar.gz"],
        check=True,
        capture_output=True
    )

    # Extract helm binary
    subprocess.run(
        ["tar", "-xzf", str(helm_tar), "-C", str(BIN_DIR),
         "--strip-components=1", "linux-amd64/helm"],
        check=True,
        capture_output=True
    )

    # Remove tar file
    helm_tar.unlink()

    # Make executable
    HELM_BIN.chmod(0o755)

    print(f"✓ helm {helm_version} installed to {HELM_BIN}")
    return str(HELM_BIN)


# =============================================================================
# Session Fixtures - kind Cluster Management
# =============================================================================

@pytest.fixture(scope="session")
def kubectl_cmd():
    """Ensure kubectl is installed and return the command"""
    return ensure_kubectl_installed()


@pytest.fixture(scope="session")
def kind_cmd():
    """Ensure kind is installed and return the command"""
    return ensure_kind_installed()


@pytest.fixture(scope="session")
def helm_cmd():
    """Ensure helm is installed and return the command"""
    return ensure_helm_installed()


@pytest.fixture(scope="session")
def kind_cluster(kind_cmd, kubectl_cmd, helm_cmd, generate_ssl_certificates, request):
    """
    Create a kind cluster for the entire test session.
    The cluster is shared across all tests for better performance.

    Args:
        generate_ssl_certificates: Fixture that ensures certificates are generated before cluster creation
    """
    # Store certificate paths for later use
    generated_certs = generate_ssl_certificates
    cluster_name = "easyhaproxy-test"

    # Register cleanup to always run, even on failure
    def cleanup():
        print(f"\n[Cleanup] Deleting kind cluster '{cluster_name}'...")
        try:
            subprocess.run(
                [kind_cmd, "delete", "cluster", "--name", cluster_name],
                capture_output=True,
                timeout=10
            )
            print("✓ Cluster deleted")
        except subprocess.TimeoutExpired:
            print("✗ Cluster deletion timed out (may still be running)")
        except Exception as e:
            print(f"✗ Cluster deletion failed: {e}")

    request.addfinalizer(cleanup)

    print(f"\n[1/9] Creating kind cluster '{cluster_name}'...")

    # Check if cluster already exists
    print("[1/9] Checking for existing cluster...")
    result = subprocess.run(
        [kind_cmd, "get", "clusters"],
        capture_output=True,
        text=True
    )

    if cluster_name in result.stdout:
        print(f"[1/9] Cluster '{cluster_name}' already exists, checking if it's healthy...")
        # Check if cluster is healthy by trying to get nodes
        result = subprocess.run(
            [kubectl_cmd, "--context", f"kind-{cluster_name}", "get", "nodes"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"[1/9] Cluster '{cluster_name}' is healthy, reusing it...")
            print("✓ Reusing existing cluster\n")
            # Skip to yield, return context
            yield {"name": cluster_name, "kubectl": kubectl_cmd, "certs": generated_certs}
            return
        else:
            print(f"[1/9] Cluster '{cluster_name}' is unhealthy, deleting and recreating...")
            subprocess.run(
                [kind_cmd, "delete", "cluster", "--name", cluster_name],
                check=True,
                capture_output=True
            )

    # Create cluster with port mappings for HAProxy
    print("[1/9] Writing cluster config...")
    cluster_config = BIN_DIR / "cluster-config.yaml"
    cluster_config.parent.mkdir(exist_ok=True)

    with open(cluster_config, 'w') as f:
        f.write(f"""kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: {HTTP_PORT}
    protocol: TCP
  - containerPort: 443
    hostPort: {HTTPS_PORT}
    protocol: TCP
  - containerPort: 1936
    hostPort: {STATS_PORT}
    protocol: TCP
""")

    print("[2/9] Creating kind cluster (this may take 1-2 minutes)...")
    subprocess.run(
        [kind_cmd, "create", "cluster", "--name", cluster_name,
         "--config", str(cluster_config)],
        check=True,
        timeout=180
    )

    print("[3/9] Setting kubectl context...")
    subprocess.run(
        [kubectl_cmd, "config", "use-context", f"kind-{cluster_name}"],
        check=True,
        capture_output=True
    )

    print("[3/9] Waiting for cluster nodes to be ready...")
    subprocess.run(
        [kubectl_cmd, "wait", "--for=condition=Ready", "nodes", "--all",
         "--timeout=30s"],
        check=True,
        timeout=35
    )

    print(f"✓ kind cluster '{cluster_name}' is ready")

    # Build and load local EasyHAProxy image
    print("[4/9] Building local EasyHAProxy image (may take 30-60s)...")
    project_root = BASE_DIR.parent
    subprocess.run(
        ["docker", "build", "-t", "byjg/easy-haproxy:local",
         "-f", str(project_root / "build" / "Dockerfile"),
         str(project_root)],
        check=True,
        capture_output=True,
        timeout=120
    )

    print("[5/9] Loading image into kind cluster (may take 10-20s)...")
    subprocess.run(
        [kind_cmd, "load", "docker-image", "byjg/easy-haproxy:local",
         "--name", cluster_name],
        check=True,
        timeout=30
    )

    # Generate EasyHAProxy manifest using Helm
    print("[6/9] Generating EasyHAProxy manifest from Helm...")
    helm_dir = project_root / "helm"
    manifest_path = BIN_DIR / "easyhaproxy-local.yml"

    result = subprocess.run(
        [helm_cmd, "template", "ingress", str(helm_dir / "easyhaproxy"),
         "--namespace", "easyhaproxy",
         "--set", "service.create=false",
         "--set", "image.tag=local",
         "--set", "image.pullPolicy=Never"],
        check=True,
        capture_output=True,
        text=True
    )

    # Write manifest to file
    print("[6/9] Writing manifest to file...")
    with open(manifest_path, 'w') as f:
        f.write(result.stdout)

    # Install EasyHAProxy
    print("[7/9] Creating easyhaproxy namespace...")
    subprocess.run(
        [kubectl_cmd, "create", "namespace", "easyhaproxy"],
        check=True
    )

    # Apply manifest
    print("[7/9] Applying EasyHAProxy manifest...")
    subprocess.run(
        [kubectl_cmd, "apply", "-f", str(manifest_path)],
        check=True
    )

    # Label the control-plane node
    print("[8/9] Labeling control-plane node...")
    subprocess.run(
        [kubectl_cmd, "label", "nodes", f"{cluster_name}-control-plane",
         "easyhaproxy/node=master", "--overwrite"],
        check=True
    )

    # Wait for EasyHAProxy to be ready
    print("[9/9] Waiting for EasyHAProxy pods to be ready...")
    try:
        subprocess.run(
            [kubectl_cmd, "wait", "--for=condition=Ready", "pods",
             "-n", "easyhaproxy", "-l", "app.kubernetes.io/name=easyhaproxy",
             "--timeout=10s"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ EasyHAProxy pods are ready")
    except subprocess.CalledProcessError as e:
        # Show pod status for debugging
        print("✗ Pods not ready within 10s. Checking status...")
        result = subprocess.run(
            [kubectl_cmd, "get", "pods", "-n", "easyhaproxy", "-o", "wide"],
            capture_output=True,
            text=True
        )
        print(result.stdout)

        # Show pod events
        result = subprocess.run(
            [kubectl_cmd, "get", "events", "-n", "easyhaproxy", "--sort-by=.lastTimestamp"],
            capture_output=True,
            text=True
        )
        print("Events:")
        print(result.stdout)
        raise

    print("✓ All setup complete! Cluster is ready for tests.\n")

    yield {"name": cluster_name, "kubectl": kubectl_cmd, "certs": generated_certs}


# =============================================================================
# Test Fixtures - Kubernetes Manifest Deployment
# =============================================================================

class KubernetesFixture:
    """Helper class to manage Kubernetes manifest lifecycle"""

    def __init__(self, manifest_file: str, kubectl_cmd: str, namespace: str = "default", wait_time: int = 5):
        self.manifest_file = str(BASE_DIR / "kubernetes" / manifest_file)
        self.kubectl = kubectl_cmd
        self.namespace = namespace
        self.wait_time = wait_time

    def apply(self):
        """Apply Kubernetes manifest"""
        print()  # Newline for better test output formatting
        # Create namespace if it doesn't exist
        if self.namespace != "default":
            subprocess.run(
                [self.kubectl, "create", "namespace", self.namespace],
                capture_output=True  # Ignore if already exists
            )

        # Apply manifest
        subprocess.run(
            [self.kubectl, "apply", "-f", self.manifest_file, "-n", self.namespace],
            check=True,
            capture_output=True
        )

        # Wait for pods to be ready
        time.sleep(self.wait_time)

        # Wait for all pods to be running
        if not wait_for_pods_ready(self.kubectl, self.namespace, timeout=60):
            raise TimeoutError(f"Pods in namespace '{self.namespace}' did not become ready within 60 seconds")

    def delete(self):
        """Delete Kubernetes resources"""
        subprocess.run(
            [self.kubectl, "delete", "-f", self.manifest_file, "-n", self.namespace,
             "--ignore-not-found=true"],
            check=True,
            capture_output=True
        )

        # Delete namespace if not default
        if self.namespace != "default":
            subprocess.run(
                [self.kubectl, "delete", "namespace", self.namespace,
                 "--ignore-not-found=true"],
                capture_output=True
            )


@pytest.fixture
def k8s_service(kind_cluster) -> Generator[str, None, None]:
    """Fixture for service.yml"""
    kubectl_cmd = kind_cluster["kubectl"]
    fixture = KubernetesFixture("service.yml", kubectl_cmd, namespace="default")
    fixture.apply()
    yield kubectl_cmd
    fixture.delete()


@pytest.fixture
def k8s_ip_whitelist(kind_cluster) -> Generator[str, None, None]:
    """Fixture for ip-whitelist.yml"""
    kubectl_cmd = kind_cluster["kubectl"]
    fixture = KubernetesFixture("ip-whitelist.yml", kubectl_cmd, namespace="default")
    fixture.apply()
    yield kubectl_cmd
    fixture.delete()


@pytest.fixture
def k8s_service_tls(kind_cluster) -> Generator[str, None, None]:
    """Fixture for service_tls.yml with generated certificates"""
    kubectl_cmd = kind_cluster["kubectl"]
    generated_certs = kind_cluster["certs"]

    # Create namespace if it doesn't exist
    subprocess.run(
        [kubectl_cmd, "create", "namespace", "default"],
        capture_output=True  # Ignore if already exists
    )

    # Create TLS secret from generated certificate
    create_tls_secret_from_pem(
        kubectl_cmd,
        secret_name="host2-tls",
        namespace="default",
        pem_file=generated_certs["host2_local"]
    )

    # Apply the manifest (without the embedded secret, we'll use ours)
    # We need to filter out the Secret from service_tls.yml
    manifest_path = BASE_DIR / "kubernetes" / "service_tls.yml"
    with open(manifest_path, 'r') as f:
        manifest_content = f.read()

    # Remove the Secret section from the manifest
    # Remove everything between "kind: Secret" and the next "---" or end of file
    manifest_filtered = re.sub(
        r'^---\s*\napiVersion: v1\s*\nkind: Secret\s*\n.*?(?=^---|\Z)',
        '',
        manifest_content,
        flags=re.MULTILINE | re.DOTALL
    )

    # Write filtered manifest to temp file in the same directory
    temp_manifest_path = BASE_DIR / "service_tls_generated.yml"
    with open(temp_manifest_path, 'w') as f:
        f.write(manifest_filtered)

    try:
        # Apply manifest using kubectl directly since we have a custom path
        subprocess.run(
            [kubectl_cmd, "apply", "-f", str(temp_manifest_path), "-n", "default"],
            check=True,
            capture_output=True
        )

        # Wait for pods to be ready
        time.sleep(5)

        # Wait for all pods to be running
        if not wait_for_pods_ready(kubectl_cmd, "default", label_selector="app=tls-example", timeout=60):
            raise TimeoutError("TLS example pods did not become ready within 60 seconds")

        yield kubectl_cmd

        # Cleanup
        subprocess.run(
            [kubectl_cmd, "delete", "-f", str(temp_manifest_path), "-n", "default",
             "--ignore-not-found=true"],
            check=True,
            capture_output=True
        )
    finally:
        # Clean up temp manifest
        if temp_manifest_path.exists():
            os.unlink(temp_manifest_path)

        # Delete the TLS secret
        subprocess.run(
            [kubectl_cmd, "delete", "secret", "host2-tls", "-n", "default",
             "--ignore-not-found=true"],
            capture_output=True
        )


@pytest.fixture
def k8s_jwt_validator_secret(kind_cluster) -> Generator[dict, None, None]:
    """Fixture for jwt-validator-secret-example.yml with generated JWT keys"""
    if not JWT_AVAILABLE:
        pytest.skip("PyJWT not available - install with: pip install pyjwt cryptography")

    kubectl_cmd = kind_cluster["kubectl"]
    generated_certs = kind_cluster["certs"]

    # Create namespace if it doesn't exist
    subprocess.run(
        [kubectl_cmd, "create", "namespace", "default"],
        capture_output=True  # Ignore if already exists
    )

    # Read the generated JWT public key
    with open(generated_certs["jwt_pubkey"], 'r') as f:
        jwt_pubkey_content = f.read()

    # Create JWT secrets using kubectl
    print()  # Newline for better test output formatting
    print("  → Creating JWT secret 'jwt-pubkey-secret'...")
    subprocess.run(
        [kubectl_cmd, "delete", "secret", "jwt-pubkey-secret", "-n", "default",
         "--ignore-not-found=true"],
        capture_output=True
    )
    subprocess.run(
        [kubectl_cmd, "create", "secret", "generic", "jwt-pubkey-secret",
         f"--from-literal=pubkey={jwt_pubkey_content}",
         "-n", "default"],
        check=True,
        capture_output=True
    )

    print("  → Creating JWT secret 'jwt-custom-secret'...")
    subprocess.run(
        [kubectl_cmd, "delete", "secret", "jwt-custom-secret", "-n", "default",
         "--ignore-not-found=true"],
        capture_output=True
    )
    subprocess.run(
        [kubectl_cmd, "create", "secret", "generic", "jwt-custom-secret",
         f"--from-literal=rsa-public-key={jwt_pubkey_content}",
         "-n", "default"],
        check=True,
        capture_output=True
    )

    # Apply manifest
    manifest_path = BASE_DIR / "kubernetes" / "jwt-validator-secret-example.yml"
    subprocess.run(
        [kubectl_cmd, "apply", "-f", str(manifest_path), "-n", "default"],
        check=True,
        capture_output=True
    )

    # Wait for pods to be ready
    time.sleep(5)

    # Wait for all pods to be running
    if not wait_for_pods_ready(kubectl_cmd, "default", label_selector="app=api", timeout=60):
        raise TimeoutError("JWT API example pods did not become ready within 60 seconds")

    # Return context with paths to JWT keys
    yield {
        "kubectl": kubectl_cmd,
        "jwt_private_key": generated_certs["jwt_private"],
        "jwt_public_key": generated_certs["jwt_pubkey"]
    }

    # Cleanup
    subprocess.run(
        [kubectl_cmd, "delete", "-f", str(manifest_path), "-n", "default",
         "--ignore-not-found=true"],
        check=True,
        capture_output=True
    )

    # Delete the JWT secrets
    subprocess.run(
        [kubectl_cmd, "delete", "secret", "jwt-pubkey-secret", "-n", "default",
         "--ignore-not-found=true"],
        capture_output=True
    )
    subprocess.run(
        [kubectl_cmd, "delete", "secret", "jwt-custom-secret", "-n", "default",
         "--ignore-not-found=true"],
        capture_output=True
    )


@pytest.fixture
def k8s_cloudflare(kind_cluster, kind_cmd) -> Generator[str, None, None]:
    """Fixture for cloudflare.yml with base64-encoded IP list"""
    kubectl_cmd = kind_cluster["kubectl"]
    cluster_name = kind_cluster["name"]

    # Build header-echo server image locally
    header_echo_dir = BASE_DIR / "fixtures" / "header-echo"
    print()  # Newline for better test output formatting
    print("  → Building header-echo-server:test image...")
    subprocess.run(
        ["docker", "build", "-t", "header-echo-server:test", str(header_echo_dir)],
        check=True,
        capture_output=True
    )

    # Load image into kind cluster
    print("  → Loading header-echo-server:test into kind cluster...")
    subprocess.run(
        [kind_cmd, "load", "docker-image", "header-echo-server:test",
         "--name", cluster_name],
        check=True,
        capture_output=True
    )

    # Create a modified cloudflare manifest with base64-encoded test IPs
    # Include 127.0.0.1 and Docker/kind network ranges so test requests work
    test_ips = [
        "127.0.0.1",           # localhost for testing
        "10.0.0.0/8",          # Private network
        "172.16.0.0/12",       # Docker default network
        "192.168.0.0/16",      # Private network
    ]

    # Base64 encode the IP list
    ip_list_content = "\n".join(test_ips)
    ip_list_base64 = base64.b64encode(ip_list_content.encode('utf-8')).decode('ascii')

    # Read the original manifest
    manifest_path = BASE_DIR / "kubernetes" / "cloudflare.yml"
    with open(manifest_path, 'r') as f:
        manifest_content = f.read()

    # Add the ip_list annotation
    # Find the annotations section and add our base64 IP list
    manifest_modified = manifest_content.replace(
        'easyhaproxy.plugins: "cloudflare"',
        f'easyhaproxy.plugins: "cloudflare"\n    easyhaproxy.plugin.cloudflare.ip_list: "{ip_list_base64}"'
    )

    # Write modified manifest to temp file
    temp_manifest_path = BASE_DIR / "kubernetes" / "cloudflare_test.yml"
    with open(temp_manifest_path, 'w') as f:
        f.write(manifest_modified)

    try:
        # Apply manifest
        subprocess.run(
            [kubectl_cmd, "apply", "-f", str(temp_manifest_path), "-n", "default"],
            check=True,
            capture_output=True
        )

        # Wait for pods to be ready
        time.sleep(5)

        # Wait for all pods to be running
        if not wait_for_pods_ready(kubectl_cmd, "default", label_selector="app=webapp", timeout=60):
            raise TimeoutError("Cloudflare webapp pods did not become ready within 60 seconds")

        yield kubectl_cmd

        # Cleanup
        subprocess.run(
            [kubectl_cmd, "delete", "-f", str(temp_manifest_path), "-n", "default",
             "--ignore-not-found=true"],
            check=True,
            capture_output=True
        )
    finally:
        # Clean up temp manifest
        if temp_manifest_path.exists():
            os.unlink(temp_manifest_path)


# =============================================================================
# Helper Functions for Tests
# =============================================================================

def wait_for_easyhaproxy_discovery(kubectl_cmd: str, expected_host: str, timeout: int = 10) -> bool:
    """
    Wait for EasyHAProxy to discover and configure the ingress host.

    This function performs multiple checks to ensure the ingress is fully ready:
    1. Backend pods are Running
    2. Ingress has an ADDRESS assigned
    3. EasyHAProxy logs show the host was discovered
    4. Simple connectivity test to HAProxy

    Args:
        kubectl_cmd: Path to kubectl command
        expected_host: The hostname to look for in logs (e.g., "example.org")
        timeout: Maximum seconds to wait (default 10)

    Returns:
        True if host is discovered and ready, False if timeout
    """
    start_time = time.time()

    # Step 1: Wait for backend pods to be Running (with ingress selector)
    print(f"  → Waiting for backend pods with host '{expected_host}' to be ready...")
    while time.time() - start_time < timeout:
        try:
            # Get all ingresses
            result = subprocess.run(
                [kubectl_cmd, "get", "ingress", "-A", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            ingresses = json.loads(result.stdout)

            # Find ingress with our host
            ingress_namespace = None
            for ing in ingresses.get('items', []):
                for rule in ing.get('spec', {}).get('rules', []):
                    if rule.get('host') == expected_host:
                        ingress_namespace = ing.get('metadata', {}).get('namespace')
                        break
                if ingress_namespace:
                    break

            if ingress_namespace:
                # Check if pods in that namespace are running using helper
                if wait_for_pods_ready(kubectl_cmd, ingress_namespace, timeout=5, verbose=False):
                    print(f"  ✓ Backend pods are Running")
                    break
        except Exception:
            pass

        time.sleep(1)

    # Step 2: Wait for ingress to have an ADDRESS assigned
    print(f"  → Waiting for ingress ADDRESS to be assigned...")
    address_found = False
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                [kubectl_cmd, "get", "ingress", "-A", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )
            ingresses = json.loads(result.stdout)

            for ing in ingresses.get('items', []):
                for rule in ing.get('spec', {}).get('rules', []):
                    if rule.get('host') == expected_host:
                        # Check if ingress has loadBalancer status
                        lb_ingress = ing.get('status', {}).get('loadBalancer', {}).get('ingress', [])
                        if lb_ingress:
                            print(f"  ✓ Ingress has ADDRESS assigned")
                            address_found = True
                            break
                if address_found:
                    break

            if address_found:
                break
        except Exception:
            pass

        time.sleep(1)

    # Step 3: Wait for EasyHAProxy to discover the host in logs
    print(f"  → Waiting for EasyHAProxy to discover '{expected_host}'...")
    while time.time() - start_time < timeout:
        # Get EasyHAProxy pod logs
        result = subprocess.run(
            [kubectl_cmd, "logs", "-n", "easyhaproxy", "-l", "app.kubernetes.io/name=easyhaproxy",
             "--tail=100"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Check if "Found hosts:" appears in logs with our expected host
        if "Found hosts:" in result.stdout and expected_host in result.stdout:
            print(f"  ✓ EasyHAProxy discovered '{expected_host}' in logs")
            break

        time.sleep(1)

    # Step 4: Simple connectivity check to HAProxy
    print(f"  → Testing connectivity to HAProxy...")
    retries = 3
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "-H", f"Host: {expected_host}", f"http://localhost:{HTTP_PORT}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            http_code = result.stdout.strip()
            # Accept 200, 503 (backend may not be ready yet), or any response that proves HAProxy is responding
            if http_code and http_code != "000":
                print(f"  ✓ HAProxy is responding (HTTP {http_code})")
                # Give HAProxy a moment to stabilize after configuration reload
                time.sleep(2)
                return True
        except Exception:
            pass

        if attempt < retries - 1:
            time.sleep(1)

    # Check if we timed out
    if time.time() - start_time >= timeout:
        print(f"  ✗ Timeout waiting for '{expected_host}' to be ready")
        return False

    return True


# =============================================================================
# Test: service.yml - Basic Service
# =============================================================================

@pytest.mark.kubernetes
class TestBasicService:
    """Tests for service.yml - Basic Kubernetes service"""

    def test_resources_created(self, k8s_service):
        """Test that deployment, service, and ingress are created"""
        kubectl = k8s_service

        # Check all resources exist
        result = subprocess.run(
            [kubectl, "get", "deployment,service,ingress", "container-example", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "container-example" in result.stdout

    def test_pods_running(self, k8s_service):
        """Test that all pods are running"""
        kubectl = k8s_service

        # Wait for deployment to be ready
        subprocess.run(
            [kubectl, "wait", "--for=condition=Available", "deployment/container-example",
             "-n", "default", "--timeout=30s"],
            check=True
        )

        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "default", "-l", "app=container-example", "-o", "json"],
            check=True,
            capture_output=True,
            text=True
        )
        pods = json.loads(result.stdout)

        assert len(pods['items']) > 0, "No container-example pods found"

        for pod in pods['items']:
            assert pod['status']['phase'] == 'Running', \
                f"Pod {pod['metadata']['name']} is not running: {pod['status']['phase']}"

    def test_http_request_example_org(self, k8s_service):
        """Test HTTP request via ingress with example.org"""
        kubectl = k8s_service

        # Wait for EasyHAProxy to discover and fully configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "example.org", timeout=30), \
            "EasyHAProxy did not become ready for example.org within 30 seconds"

        # Test HTTP request
        result = subprocess.run(
            ["curl", "-s", "-H", "Host: example.org", f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert "My Host Example" in result.stdout, \
            f"Expected 'My Host Example' in response, got: {result.stdout}"

    def test_http_request_www_example_org(self, k8s_service):
        """Test HTTP request via ingress with www.example.org"""
        kubectl = k8s_service

        # Wait for EasyHAProxy to discover and fully configure the ingress
        # (Even though example.org was checked in the previous test, we should verify www.example.org too)
        assert wait_for_easyhaproxy_discovery(kubectl, "www.example.org", timeout=30), \
            "EasyHAProxy did not become ready for www.example.org within 30 seconds"

        # Test HTTP request
        result = subprocess.run(
            ["curl", "-s", "-H", "Host: www.example.org", f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert "My Host Example" in result.stdout, \
            f"Expected 'My Host Example' in response for www.example.org, got: {result.stdout}"


# =============================================================================
# Test: service_tls.yml - TLS/SSL Service
# =============================================================================

@pytest.mark.kubernetes
class TestTLSService:
    """Tests for service_tls.yml - TLS/SSL ingress with custom certificates"""

    def test_resources_created(self, k8s_service_tls):
        """Test that deployment, service, ingress, and secret are created"""
        kubectl = k8s_service_tls

        # Check deployment, service, and ingress exist
        result = subprocess.run(
            [kubectl, "get", "deployment,service,ingress", "tls-example", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "tls-example" in result.stdout

        # Verify TLS secret exists (separate check since it has different name)
        result = subprocess.run(
            [kubectl, "get", "secret", "host2-tls", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "host2-tls" in result.stdout
        assert "kubernetes.io/tls" in result.stdout

    def test_pods_running(self, k8s_service_tls):
        """Test that all pods are running"""
        kubectl = k8s_service_tls

        # Wait for deployment to be ready
        subprocess.run(
            [kubectl, "wait", "--for=condition=Available", "deployment/tls-example",
             "-n", "default", "--timeout=30s"],
            check=True
        )

        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "default", "-l", "app=tls-example", "-o", "json"],
            check=True,
            capture_output=True,
            text=True
        )
        pods = json.loads(result.stdout)

        assert len(pods['items']) > 0, "No tls-example pods found"

        for pod in pods['items']:
            assert pod['status']['phase'] == 'Running', \
                f"Pod {pod['metadata']['name']} is not running: {pod['status']['phase']}"

    def test_https_request_host2_local(self, k8s_service_tls):
        """Test HTTPS request via ingress with host2.local"""
        kubectl = k8s_service_tls

        # Wait for EasyHAProxy to discover and fully configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "host2.local", timeout=30), \
            "EasyHAProxy did not become ready for host2.local within 30 seconds"

        # Test HTTPS request (using -k to allow self-signed certificate)
        result = subprocess.run(
            ["curl", "-k", "-s", "-H", "Host: host2.local", f"https://localhost:{HTTPS_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert "My Host Example" in result.stdout, \
            f"Expected 'My Host Example' in response, got: {result.stdout}"


# =============================================================================
# Test: ip-whitelist.yml - IP Whitelist Plugin
# =============================================================================

@pytest.mark.kubernetes
class TestIPWhitelist:
    """Tests for ip-whitelist.yml - IP whitelist plugin"""

    def test_resources_created(self, k8s_ip_whitelist):
        """Test that deployment, service, and ingress are created"""
        kubectl = k8s_ip_whitelist

        # Check deployment exists
        result = subprocess.run(
            [kubectl, "get", "deployment", "admin", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "admin" in result.stdout

        # Check service exists
        result = subprocess.run(
            [kubectl, "get", "service", "admin-service", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "admin-service" in result.stdout

        # Check ingress exists
        result = subprocess.run(
            [kubectl, "get", "ingress", "admin-ingress-whitelist", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "admin-ingress-whitelist" in result.stdout

    def test_pods_running(self, k8s_ip_whitelist):
        """Test that all admin pods are running"""
        kubectl = k8s_ip_whitelist

        # Wait for deployment to be ready
        subprocess.run(
            [kubectl, "wait", "--for=condition=Available", "deployment/admin",
             "-n", "default", "--timeout=30s"],
            check=True
        )

        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "default", "-l", "app=admin", "-o", "json"],
            check=True,
            capture_output=True,
            text=True
        )
        pods = json.loads(result.stdout)

        assert len(pods['items']) > 0, "No admin pods found"

        for pod in pods['items']:
            assert pod['status']['phase'] == 'Running', \
                f"Pod {pod['metadata']['name']} is not running: {pod['status']['phase']}"

    def test_haproxy_config_has_ip_whitelist(self, k8s_ip_whitelist):
        """Test that HAProxy configuration contains IP whitelist rules"""
        kubectl = k8s_ip_whitelist

        # Wait for EasyHAProxy to discover the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "admin.example.local", timeout=30), \
            "EasyHAProxy did not discover admin.example.local within 30 seconds"

        # Get the EasyHAProxy pod name
        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "easyhaproxy",
             "-l", "app.kubernetes.io/name=easyhaproxy",
             "-o", "jsonpath={.items[0].metadata.name}"],
            check=True,
            capture_output=True,
            text=True
        )
        pod_name = result.stdout.strip()
        assert pod_name, "EasyHAProxy pod not found"

        # Get HAProxy configuration
        result = subprocess.run(
            [kubectl, "exec", "-n", "easyhaproxy", pod_name,
             "--", "cat", "/etc/haproxy/haproxy.cfg"],
            check=True,
            capture_output=True,
            text=True
        )
        config = result.stdout

        # Extract the specific backend block for admin service
        # Backend name format: srv_{hostname_with_underscores}_{port}
        backend_block = extract_backend_block(config, "srv_admin_example_local_80")
        assert backend_block, "Backend srv_admin_example_local_80 not found"

        # Verify IP whitelist plugin comment is in this backend
        assert "# IP Whitelist - Only allow specific IPs" in backend_block, \
            "IP Whitelist plugin comment not found in admin backend"

        # Verify ACL for whitelisted IPs is in this backend
        assert "acl whitelisted_ip src" in backend_block, \
            "IP whitelist ACL not found in admin backend"

        # Extract the ACL line to verify IPs
        acl_line = [line for line in backend_block.split('\n') if 'acl whitelisted_ip src' in line][0]
        assert "127.0.0.1" in acl_line, "Localhost not in allowed IPs"
        assert "10.0.0.0/8" in acl_line, "10.0.0.0/8 network not in allowed IPs"
        assert "172.16.0.0/12" in acl_line, "172.16.0.0/12 network not in allowed IPs"

        # Verify deny rule for non-whitelisted IPs is in this backend
        assert "http-request deny deny_status 403 if !whitelisted_ip" in backend_block, \
            "Deny rule for non-whitelisted IPs not found in admin backend"

    def test_access_from_localhost(self, k8s_ip_whitelist):
        """Test that access from localhost is allowed"""
        kubectl = k8s_ip_whitelist

        # Wait for EasyHAProxy to discover and configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "admin.example.local", timeout=30), \
            "EasyHAProxy did not become ready for admin.example.local within 30 seconds"

        # Test HTTP request (localhost should be in allowed IPs)
        result = subprocess.run(
            ["curl", "-s", "-H", "Host: admin.example.local", f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert "Admin Panel - IP Restricted" in result.stdout, \
            f"Expected 'Admin Panel - IP Restricted' in response, got: {result.stdout}"


# =============================================================================
# Test: jwt-validator-secret-example.yml - JWT Validator with Kubernetes Secrets
# =============================================================================

@pytest.mark.kubernetes
class TestJWTValidatorSecret:
    """Tests for jwt-validator-secret-example.yml - JWT validation using Kubernetes secrets"""

    def test_resources_created(self, k8s_jwt_validator_secret):
        """Test that secrets, service, and ingresses are created"""
        kubectl = k8s_jwt_validator_secret["kubectl"]

        # Check secrets exist
        result = subprocess.run(
            [kubectl, "get", "secret", "jwt-pubkey-secret", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "jwt-pubkey-secret" in result.stdout

        result = subprocess.run(
            [kubectl, "get", "secret", "jwt-custom-secret", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "jwt-custom-secret" in result.stdout

        # Check service exists
        result = subprocess.run(
            [kubectl, "get", "service", "api-service", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "api-service" in result.stdout

        # Check both ingresses exist
        result = subprocess.run(
            [kubectl, "get", "ingress", "api-ingress-jwt-auto", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "api-ingress-jwt-auto" in result.stdout

        result = subprocess.run(
            [kubectl, "get", "ingress", "api-ingress-jwt-explicit", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "api-ingress-jwt-explicit" in result.stdout

    def test_pods_running(self, k8s_jwt_validator_secret):
        """Test that all API pods are running"""
        kubectl = k8s_jwt_validator_secret["kubectl"]

        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "default", "-l", "app=api", "-o", "json"],
            check=True,
            capture_output=True,
            text=True
        )
        pods = json.loads(result.stdout)

        assert len(pods['items']) > 0, "No API pods found"

        for pod in pods['items']:
            assert pod['status']['phase'] == 'Running', \
                f"Pod {pod['metadata']['name']} is not running: {pod['status']['phase']}"

    def test_haproxy_config_has_jwt_validation(self, k8s_jwt_validator_secret):
        """Test that HAProxy configuration contains JWT validation rules"""
        kubectl = k8s_jwt_validator_secret["kubectl"]

        # Wait for EasyHAProxy to discover the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "api.example.local", timeout=30), \
            "EasyHAProxy did not discover api.example.local within 30 seconds"

        # Get the EasyHAProxy pod name
        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "easyhaproxy",
             "-l", "app.kubernetes.io/name=easyhaproxy",
             "-o", "jsonpath={.items[0].metadata.name}"],
            check=True,
            capture_output=True,
            text=True
        )
        pod_name = result.stdout.strip()
        assert pod_name, "EasyHAProxy pod not found"

        # Get HAProxy configuration
        result = subprocess.run(
            [kubectl, "exec", "-n", "easyhaproxy", pod_name,
             "--", "cat", "/etc/haproxy/haproxy.cfg"],
            check=True,
            capture_output=True,
            text=True
        )
        config = result.stdout

        # Extract the specific backend block for API service
        # Backend name format: srv_{hostname_with_underscores}_{port}
        backend_block = extract_backend_block(config, "srv_api_example_local_80")
        assert backend_block, "Backend srv_api_example_local_80 not found"

        # Verify JWT Validator plugin comment is in this backend
        assert "# JWT Validator - Validate JWT tokens" in backend_block, \
            "JWT Validator plugin comment not found in API backend"

        # Verify JWT extraction is in this backend
        assert "http_auth_bearer,jwt_header_query" in backend_block, \
            "JWT header extraction not found in API backend"
        assert "http_auth_bearer,jwt_payload_query" in backend_block, \
            "JWT payload extraction not found in API backend"

        # Verify JWT validation rules are in this backend
        assert "jwt_verify" in backend_block, \
            "JWT signature verification not found in API backend"

        # Verify issuer validation is in this backend
        assert "https://auth.example.com/" in backend_block, \
            "JWT issuer validation not found in API backend"

        # Verify audience validation is in this backend
        assert "https://api.example.com" in backend_block, \
            "JWT audience validation not found in API backend"

        # Verify JWT keys directory is used in this backend
        assert "/etc/haproxy/jwt_keys/" in backend_block, \
            "JWT keys directory not found in API backend"

    def test_access_without_token_denied(self, k8s_jwt_validator_secret):
        """Test that access without Authorization header is denied"""
        kubectl = k8s_jwt_validator_secret["kubectl"]

        # Wait for EasyHAProxy to discover and configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "api.example.local", timeout=30), \
            "EasyHAProxy did not become ready for api.example.local within 30 seconds"

        # Test HTTP request without Authorization header (should be denied)
        result = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-H", "Host: api.example.local",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Extract HTTP status code from last line
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1]

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert http_code == "403", \
            f"Expected HTTP 403 for missing Authorization header, got: {http_code}"
        assert "Missing Authorization HTTP header" in result.stdout, \
            f"Expected 'Missing Authorization HTTP header' in response, got: {result.stdout}"

    def test_access_with_valid_token_allowed(self, k8s_jwt_validator_secret):
        """Test that access with valid JWT token is allowed"""
        kubectl = k8s_jwt_validator_secret["kubectl"]
        jwt_private_key = k8s_jwt_validator_secret["jwt_private_key"]

        # Wait for EasyHAProxy to discover and configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "api.example.local", timeout=30), \
            "EasyHAProxy did not become ready for api.example.local within 30 seconds"

        # Generate valid JWT token
        token = generate_jwt_token(
            jwt_private_key,
            issuer="https://auth.example.com/",
            audience="https://api.example.com",
            expired=False
        )

        # Test HTTP request with valid token (should succeed)
        result = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-H", "Host: api.example.local",
             "-H", f"Authorization: Bearer {token}",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Extract HTTP status code from last line
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1]

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert http_code == "200", \
            f"Expected HTTP 200 for valid JWT token, got: {http_code}\nResponse: {result.stdout}"

    def test_access_with_expired_token_denied(self, k8s_jwt_validator_secret):
        """Test that access with expired JWT token is denied"""
        kubectl = k8s_jwt_validator_secret["kubectl"]
        jwt_private_key = k8s_jwt_validator_secret["jwt_private_key"]

        # Wait for EasyHAProxy to discover and configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "api.example.local", timeout=30), \
            "EasyHAProxy did not become ready for api.example.local within 30 seconds"

        # Generate expired JWT token
        token = generate_jwt_token(
            jwt_private_key,
            issuer="https://auth.example.com/",
            audience="https://api.example.com",
            expired=True
        )

        # Test HTTP request with expired token (should be denied)
        result = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-H", "Host: api.example.local",
             "-H", f"Authorization: Bearer {token}",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Extract HTTP status code from last line
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1]

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert http_code == "403", \
            f"Expected HTTP 403 for expired JWT token, got: {http_code}"
        assert "JWT has expired" in result.stdout, \
            f"Expected 'JWT has expired' in response, got: {result.stdout}"

    def test_access_with_wrong_issuer_denied(self, k8s_jwt_validator_secret):
        """Test that access with wrong issuer is denied"""
        kubectl = k8s_jwt_validator_secret["kubectl"]
        jwt_private_key = k8s_jwt_validator_secret["jwt_private_key"]

        # Wait for EasyHAProxy to discover and configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "api.example.local", timeout=30), \
            "EasyHAProxy did not become ready for api.example.local within 30 seconds"

        # Generate JWT token with wrong issuer
        token = generate_jwt_token(
            jwt_private_key,
            issuer="https://wrong-issuer.example.com/",  # Wrong issuer
            audience="https://api.example.com",
            expired=False
        )

        # Test HTTP request with wrong issuer (should be denied)
        result = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-H", "Host: api.example.local",
             "-H", f"Authorization: Bearer {token}",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Extract HTTP status code from last line
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1]

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert http_code == "403", \
            f"Expected HTTP 403 for wrong JWT issuer, got: {http_code}"
        assert "Invalid JWT issuer" in result.stdout, \
            f"Expected 'Invalid JWT issuer' in response, got: {result.stdout}"

    def test_explicit_key_ingress(self, k8s_jwt_validator_secret):
        """Test that the explicit key format ingress also works"""
        kubectl = k8s_jwt_validator_secret["kubectl"]
        jwt_private_key = k8s_jwt_validator_secret["jwt_private_key"]

        # Wait for EasyHAProxy to discover the explicit key ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "api-custom.example.local", timeout=30), \
            "EasyHAProxy did not discover api-custom.example.local within 30 seconds"

        # Generate valid JWT token
        token = generate_jwt_token(
            jwt_private_key,
            issuer="https://auth.example.com/",
            audience="https://api.example.com",
            expired=False
        )

        # Test HTTP request with valid token on explicit key ingress
        result = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-H", "Host: api-custom.example.local",
             "-H", f"Authorization: Bearer {token}",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Extract HTTP status code from last line
        lines = result.stdout.strip().split('\n')
        http_code = lines[-1]

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"
        assert http_code == "200", \
            f"Expected HTTP 200 for valid JWT token on explicit key ingress, got: {http_code}\nResponse: {result.stdout}"


# =============================================================================
# Test: cloudflare.yml - Cloudflare IP Restoration Plugin
# =============================================================================

@pytest.mark.kubernetes
class TestCloudflare:
    """Tests for cloudflare.yml - Cloudflare IP restoration from CDN"""

    def test_resources_created(self, k8s_cloudflare):
        """Test that deployment, service, and ingress are created"""
        kubectl = k8s_cloudflare

        # Check deployment exists
        result = subprocess.run(
            [kubectl, "get", "deployment", "webapp", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "webapp" in result.stdout

        # Check service exists
        result = subprocess.run(
            [kubectl, "get", "service", "webapp-service", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "webapp-service" in result.stdout

        # Check ingress exists
        result = subprocess.run(
            [kubectl, "get", "ingress", "webapp-ingress-cloudflare", "-n", "default"],
            check=True,
            capture_output=True,
            text=True
        )
        assert "webapp-ingress-cloudflare" in result.stdout

    def test_pods_running(self, k8s_cloudflare):
        """Test that all webapp pods are running"""
        kubectl = k8s_cloudflare

        # Wait for deployment to be ready
        subprocess.run(
            [kubectl, "wait", "--for=condition=Available", "deployment/webapp",
             "-n", "default", "--timeout=30s"],
            check=True
        )

        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "default", "-l", "app=webapp", "-o", "json"],
            check=True,
            capture_output=True,
            text=True
        )
        pods = json.loads(result.stdout)

        assert len(pods['items']) > 0, "No webapp pods found"

        for pod in pods['items']:
            assert pod['status']['phase'] == 'Running', \
                f"Pod {pod['metadata']['name']} is not running: {pod['status']['phase']}"

    def test_haproxy_config_has_cloudflare_plugin(self, k8s_cloudflare):
        """Test that HAProxy configuration contains Cloudflare plugin rules"""
        kubectl = k8s_cloudflare

        # Wait for EasyHAProxy to discover the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "myapp.example.local", timeout=30), \
            "EasyHAProxy did not discover myapp.example.local within 30 seconds"

        # Get the EasyHAProxy pod name
        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "easyhaproxy",
             "-l", "app.kubernetes.io/name=easyhaproxy",
             "-o", "jsonpath={.items[0].metadata.name}"],
            check=True,
            capture_output=True,
            text=True
        )
        pod_name = result.stdout.strip()
        assert pod_name, "EasyHAProxy pod not found"

        # Get HAProxy configuration
        result = subprocess.run(
            [kubectl, "exec", "-n", "easyhaproxy", pod_name,
             "--", "cat", "/etc/haproxy/haproxy.cfg"],
            check=True,
            capture_output=True,
            text=True
        )
        config = result.stdout

        # Extract the specific backend block for myapp service
        # Backend name format: srv_{hostname_with_underscores}_{port}
        backend_block = extract_backend_block(config, "srv_myapp_example_local_80")
        assert backend_block, "Backend srv_myapp_example_local_80 not found"

        # Verify Cloudflare plugin comment is in this backend
        assert "# Cloudflare - Restore original visitor IP" in backend_block, \
            "Cloudflare plugin comment not found in myapp backend"

        # Verify ACL for Cloudflare IPs is in this backend
        assert "acl from_cloudflare src -f /etc/haproxy/cloudflare_ips.lst" in backend_block, \
            "Cloudflare IP ACL not found in myapp backend"

        # Verify real IP extraction from CF-Connecting-IP header is in this backend
        assert "http-request set-var(txn.real_ip) req.hdr(CF-Connecting-IP) if from_cloudflare" in backend_block, \
            "CF-Connecting-IP header extraction not found in myapp backend"

        # Verify X-Forwarded-For header update is in this backend
        assert "http-request set-header X-Forwarded-For %[var(txn.real_ip)] if from_cloudflare" in backend_block, \
            "X-Forwarded-For header update not found in myapp backend"

    def test_cloudflare_ip_file_contains_custom_ips(self, k8s_cloudflare):
        """Test that custom base64-encoded IP list was written to the IP file"""
        kubectl = k8s_cloudflare

        # Wait for EasyHAProxy to discover the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "myapp.example.local", timeout=30), \
            "EasyHAProxy did not discover myapp.example.local within 30 seconds"

        # Get the EasyHAProxy pod name
        result = subprocess.run(
            [kubectl, "get", "pods", "-n", "easyhaproxy",
             "-l", "app.kubernetes.io/name=easyhaproxy",
             "-o", "jsonpath={.items[0].metadata.name}"],
            check=True,
            capture_output=True,
            text=True
        )
        pod_name = result.stdout.strip()

        # Read the Cloudflare IP list file
        result = subprocess.run(
            [kubectl, "exec", "-n", "easyhaproxy", pod_name,
             "--", "cat", "/etc/haproxy/cloudflare_ips.lst"],
            check=True,
            capture_output=True,
            text=True
        )
        ip_file_content = result.stdout

        # Verify our custom IPs are in the file (from fixture)
        assert "127.0.0.1" in ip_file_content, "127.0.0.1 not found in IP list"
        assert "10.0.0.0/8" in ip_file_content, "10.0.0.0/8 not found in IP list"
        assert "172.16.0.0/12" in ip_file_content, "172.16.0.0/12 not found in IP list"
        assert "192.168.0.0/16" in ip_file_content, "192.168.0.0/16 not found in IP list"

        # Verify it DOESN'T contain built-in Cloudflare IPs
        # (proves that ip_list took precedence over use_builtin_ips)
        assert "173.245.48.0/20" not in ip_file_content, \
            "Built-in Cloudflare IP found (ip_list should take precedence)"

    def test_access_to_webapp(self, k8s_cloudflare):
        """Test that the webapp is accessible and returns JSON"""
        kubectl = k8s_cloudflare

        # Wait for EasyHAProxy to discover and configure the ingress
        assert wait_for_easyhaproxy_discovery(kubectl, "myapp.example.local", timeout=30), \
            "EasyHAProxy did not become ready for myapp.example.local within 30 seconds"

        # Test HTTP request
        result = subprocess.run(
            ["curl", "-s", "-H", "Host: myapp.example.local",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Curl failed with return code {result.returncode}"

        # Parse JSON response
        data = json.loads(result.stdout)

        # Verify JSON structure
        assert "headers" in data, "Response should contain 'headers' field"
        assert "client_ip" in data, "Response should contain 'client_ip' field"
        assert "x_forwarded_for" in data, "Response should contain 'x_forwarded_for' field"

    def test_cloudflare_ip_translation_works(self, k8s_cloudflare):
        """Test that Cloudflare plugin actually translates CF-Connecting-IP to X-Forwarded-For"""
        kubectl = k8s_cloudflare

        # Wait for EasyHAProxy to be ready
        assert wait_for_easyhaproxy_discovery(kubectl, "myapp.example.local", timeout=30), \
            "EasyHAProxy did not become ready within 30 seconds"

        # Send request with CF-Connecting-IP header
        test_ip = "203.0.113.50"
        result = subprocess.run(
            ["curl", "-s",
             "-H", "Host: myapp.example.local",
             "-H", f"CF-Connecting-IP: {test_ip}",
             f"http://localhost:{HTTP_PORT}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, f"Curl failed"

        # Parse JSON response from header-echo server
        data = json.loads(result.stdout)

        # VERIFY: X-Forwarded-For was set to the CF-Connecting-IP value
        # This proves the Cloudflare plugin actually works, not just that config exists
        assert data['x_forwarded_for'] == test_ip, \
            f"Expected X-Forwarded-For to be '{test_ip}' (from CF-Connecting-IP), " \
            f"got '{data['x_forwarded_for']}'. Cloudflare IP translation NOT working!"

        # Verify client_ip is still the HAProxy/ingress IP (connection doesn't change)
        assert data['client_ip'] != test_ip, \
            f"client_ip should be HAProxy pod IP, not the translated IP"


# =============================================================================
# Helper functions for manual testing
# =============================================================================

def run_manual_test(manifest_file: str):
    """
    Helper function to run a test manually without pytest

    Example:
        run_manual_test("service.yml")
    """
    kind_bin = ensure_kind_installed()
    kubectl_bin = ensure_kubectl_installed()

    cluster_name = "easyhaproxy-manual-test"

    print(f"Creating cluster '{cluster_name}'...")
    subprocess.run(
        [kind_bin, "create", "cluster", "--name", cluster_name],
        check=True
    )

    # Wait for cluster to be ready
    subprocess.run(
        [kubectl_bin, "wait", "--for=condition=Ready", "nodes", "--all",
         "--timeout=120s"],
        check=True
    )

    fixture = None
    try:
        fixture = KubernetesFixture(manifest_file, kubectl_bin)
        fixture.apply()
        print("✅ Resources deployed successfully!")
        print("\nPress Enter to cleanup...")
        input()
    finally:
        if fixture:
            fixture.delete()
        subprocess.run(
            [kind_bin, "delete", "cluster", "--name", cluster_name],
            check=True
        )
        print("✅ Cleanup complete!")


if __name__ == "__main__":
    print("This is a pytest test suite. Run with: pytest test_kubernetes.py -v")
    print("\nAvailable test classes:")
    print("  - TestBasicService: Basic Kubernetes service tests")
    print("  - TestTLSService: TLS/SSL ingress with custom certificates")
    print("  - TestIPWhitelist: IP whitelist plugin tests")
    print("  - TestJWTValidatorSecret: JWT validation with Kubernetes secrets")