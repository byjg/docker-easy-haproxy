#!/bin/bash
set -e

# Generate SSL Certificates and JWT Keys for EasyHAProxy Examples
# This script creates all .pem files needed for the examples directory

echo "Generating SSL certificates and JWT keys for EasyHAProxy examples..."
echo ""

# Create necessary directories
mkdir -p examples/static
mkdir -p examples/docker
mkdir -p examples/docker/certs/haproxy
mkdir -p examples/swarm/certs

# ============================================================================
# Generate SSL Certificate for host1.local (4096-bit RSA, 10-year validity)
# ============================================================================
echo "Generating host1.local certificate (4096-bit RSA, 10-year validity)..."
openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
    -keyout examples/static/host1.local.pem \
    -out examples/static/host1.local.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=host1.local"

# Copy to swarm directory
cp examples/static/host1.local.pem examples/swarm/certs/host1.local.pem
echo " Created host1.local.pem (4096-bit, 10 years)"
echo "  - examples/static/host1.local.pem"
echo "  - examples/swarm/certs/host1.local.pem"
echo ""

# ============================================================================
# Generate SSL Certificate for host2.local (2048-bit RSA, 1-year validity)
# ============================================================================
echo "Generating host2.local certificate (2048-bit RSA, 1-year validity)..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout examples/docker/host2.local.pem \
    -out examples/docker/host2.local.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=host2.local"

# Copy to swarm directory
cp examples/docker/host2.local.pem examples/swarm/certs/host2.local.pem
echo " Created host2.local.pem (2048-bit, 1 year)"
echo "  - examples/docker/host2.local.pem"
echo "  - examples/swarm/certs/host2.local.pem"
echo ""

# ============================================================================
# Generate JWT RSA Key Pair (2048-bit)
# ============================================================================
echo "Generating JWT RSA key pair (2048-bit)..."

# Generate private key
openssl genrsa -out examples/docker/jwt_private.pem 2048

# Extract public key
openssl rsa -in examples/docker/jwt_private.pem -pubout -out examples/docker/jwt_pubkey.pem

echo " Created JWT key pair (2048-bit)"
echo "  - examples/docker/jwt_private.pem (private key)"
echo "  - examples/docker/jwt_pubkey.pem (public key)"
echo ""

# ============================================================================
# Generate Placeholder Certificate
# ============================================================================
echo "Generating placeholder certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout examples/docker/certs/haproxy/.place_holder_cert.pem \
    -out examples/docker/certs/haproxy/.place_holder_cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=placeholder"

echo " Created placeholder certificate"
echo "  - examples/docker/certs/haproxy/.place_holder_cert.pem"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "============================================"
echo "All certificates and keys generated successfully!"
echo "============================================"
echo ""
echo "SSL Certificates:"
echo "  - host1.local (4096-bit, 10 years)"
echo "  - host2.local (2048-bit, 1 year)"
echo ""
echo "JWT Keys:"
echo "  - jwt_private.pem (private key for signing)"
echo "  - jwt_pubkey.pem (public key for validation)"
echo ""
echo "IMPORTANT NOTES:"
echo "  - These are self-signed certificates for TESTING ONLY"
echo "  - DO NOT use these certificates in production"
echo "  - Browsers will show security warnings for self-signed certificates"
echo "  - JWT keys should be kept secure and rotated regularly"
echo ""
