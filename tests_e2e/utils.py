"""
Utility functions for EasyHAProxy integration tests.

This module provides non-fixture helper functions used across test files.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
import jwt as jwt_lib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# Track if Docker image has been built in this test session
_docker_image_built = False


class DockerComposeFixture:
    """Helper class to manage docker-compose lifecycle"""

    def __init__(self, compose_file: str, startup_wait: int = 3, build: bool = None):
        self.compose_file = compose_file
        self.startup_wait = startup_wait

        # Smart build strategy: build on first call, skip on subsequent calls
        global _docker_image_built
        if build is None:
            self.build = not _docker_image_built
        else:
            self.build = build

    def up(self):
        """Start docker-compose services"""
        global _docker_image_built

        compose_name = Path(self.compose_file).name
        print()  # Newline for better test output formatting
        print(f"  → Starting services from {compose_name}...")

        cmd = ["docker", "compose", "-f", self.compose_file, "up", "-d"]
        if self.build:
            cmd.append("--build")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ✗ ERROR: Failed to start services!")
            print(f"    stdout: {result.stdout}")
            print(f"    stderr: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

        # Mark image as built for this test session
        if self.build:
            _docker_image_built = True

        print(f"  ✓ Services started, waiting {self.startup_wait}s for initialization...")
        time.sleep(self.startup_wait)
        print(f"  ✓ Services ready")

    def down(self):
        """Stop and remove docker-compose services"""
        compose_name = Path(self.compose_file).name
        print(f"  → Stopping services from {compose_name}...")

        result = subprocess.run(
            ["docker", "compose", "-f", self.compose_file, "down", "--remove-orphans"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ⚠ WARNING: Failed to stop services cleanly")
            print(f"    stderr: {result.stderr}")
            # Don't raise error on cleanup, just warn
        else:
            print(f"  ✓ Services stopped and cleaned up")


def generate_jwt_token(
    private_key_path: Path,
    issuer: str,
    audience: str,
    expired: bool = False,
    expiration_seconds: int = 3600
) -> str:
    """
    Generate a JWT token for testing.

    This uses the sophisticated K8s implementation with proper RSA key loading
    and expiration handling.

    Args:
        private_key_path: Path to RSA private key (PEM format)
        issuer: JWT issuer claim (iss)
        audience: JWT audience claim (aud)
        expired: If True, generate an already-expired token
        expiration_seconds: Token validity duration in seconds (default 1 hour)

    Returns:
        JWT token string
    """
    # Read and parse private key
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )

    # Set expiration
    if expired:
        exp = int(time.time()) - 3600  # Expired 1 hour ago
    else:
        exp = int(time.time()) + expiration_seconds

    # Create JWT payload
    payload = {
        'iss': issuer,
        'aud': audience,
        'exp': exp,
        'sub': 'test-user',
        'iat': int(time.time())
    }

    return jwt_lib.encode(payload, private_key, algorithm='RS256')


def wait_for_pods_ready(
    kubectl_cmd: str,
    namespace: str,
    label_selector: str = None,
    timeout: int = 60,
    verbose: bool = True
) -> bool:
    """
    Wait for all pods in a namespace to be Running.

    This eliminates the duplicated wait pattern that appears 5+ times
    in the Kubernetes test file.

    Args:
        kubectl_cmd: Path to kubectl command
        namespace: Kubernetes namespace
        label_selector: Optional label selector (e.g., "app=api")
        timeout: Maximum seconds to wait
        verbose: Print status messages

    Returns:
        True if all pods running, False if timeout
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        cmd = [kubectl_cmd, "get", "pods", "-n", namespace, "-o", "json"]
        if label_selector:
            cmd.extend(["-l", label_selector])

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        pods = json.loads(result.stdout)

        if not pods['items']:
            time.sleep(2)
            continue

        all_running = all(
            pod['status']['phase'] == 'Running'
            for pod in pods['items']
        )

        if all_running:
            if verbose:
                label_info = f" (label: {label_selector})" if label_selector else ""
                print(f"  ✓ All pods running in '{namespace}'{label_info}")
            return True

        time.sleep(2)

    return False


def extract_backend_block(config: str, backend_name: str) -> str:
    """
    Extract a specific backend block from HAProxy configuration.

    Used by Docker Compose tests to verify HAProxy config contains expected rules.

    Args:
        config: Full HAProxy configuration content
        backend_name: Name of backend to extract (e.g., "srv_host1_local_443")

    Returns:
        Backend block as string, or empty string if not found
    """
    lines = config.split('\n')
    backend_lines = []
    in_backend = False

    for line in lines:
        if line.startswith(f'backend {backend_name}'):
            in_backend = True
            backend_lines.append(line)
        elif in_backend:
            # Stop when we hit another backend, frontend, or global section
            if line.startswith(('backend ', 'frontend ', 'global ', 'defaults ')):
                break
            backend_lines.append(line)

    return '\n'.join(backend_lines)


def create_tls_secret_from_pem(kubectl_cmd: str, secret_name: str, namespace: str, pem_file: Path):
    """
    Create a Kubernetes TLS secret from a PEM file.

    Used by Kubernetes tests to create TLS secrets from generated certificates.

    Args:
        kubectl_cmd: Path to kubectl command
        secret_name: Name for the secret
        namespace: Namespace to create the secret in
        pem_file: Path to the PEM file containing both certificate and key
    """
    print()  # Newline for better test output formatting
    print(f"  → Creating TLS secret '{secret_name}' from {pem_file.name}...")

    # Read the PEM file
    with open(pem_file, 'r') as f:
        pem_content = f.read()

    # Split certificate and key (PEM file contains both)
    cert_start = pem_content.find('-----BEGIN CERTIFICATE-----')
    cert_end = pem_content.find('-----END CERTIFICATE-----') + len('-----END CERTIFICATE-----')
    key_start = pem_content.find('-----BEGIN PRIVATE KEY-----')
    key_end = pem_content.find('-----END PRIVATE KEY-----') + len('-----END PRIVATE KEY-----')

    # Handle RSA PRIVATE KEY format (openssl genrsa format)
    if key_start == -1:
        key_start = pem_content.find('-----BEGIN RSA PRIVATE KEY-----')
        key_end = pem_content.find('-----END RSA PRIVATE KEY-----') + len('-----END RSA PRIVATE KEY-----')

    if cert_start == -1 or key_start == -1:
        raise ValueError(f"Invalid PEM file format in {pem_file}")

    cert = pem_content[cert_start:cert_end]
    key = pem_content[key_start:key_end]

    # Create temp files for cert and key
    with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as cert_file:
        cert_file.write(cert)
        cert_path = cert_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as key_file:
        key_file.write(key)
        key_path = key_file.name

    try:
        # Delete secret if it exists
        subprocess.run(
            [kubectl_cmd, "delete", "secret", secret_name, "-n", namespace,
             "--ignore-not-found=true"],
            capture_output=True
        )

        # Create secret using kubectl
        subprocess.run(
            [kubectl_cmd, "create", "secret", "tls", secret_name,
             f"--cert={cert_path}",
             f"--key={key_path}",
             "-n", namespace],
            check=True,
            capture_output=True
        )

        print(f"  ✓ TLS secret '{secret_name}' created")
    finally:
        # Clean up temp files
        os.unlink(cert_path)
        os.unlink(key_path)