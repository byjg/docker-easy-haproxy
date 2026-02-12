#!/bin/bash
set -e

# Generate SSL Certificates and JWT Keys for EasyHAProxy Examples
# This script creates all .pem files needed for the examples directory

echo "Generating SSL certificates and JWT keys for EasyHAProxy examples..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create necessary directories
mkdir -p "$SCRIPT_DIR/static"
mkdir -p "$SCRIPT_DIR/docker"
mkdir -p "$SCRIPT_DIR/docker/certs/haproxy"
mkdir -p "$SCRIPT_DIR/swarm/certs"

# ============================================================================
# Generate SSL Certificate for host1.local (4096-bit RSA, 10-year validity)
# ============================================================================
echo "Generating host1.local certificate (4096-bit RSA, 10-year validity)..."
openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
    -keyout "$SCRIPT_DIR/static/host1.local.pem" \
    -out "$SCRIPT_DIR/static/host1.local.pem" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=host1.local"

# Copy to swarm directory
cp "$SCRIPT_DIR/static/host1.local.pem" "$SCRIPT_DIR/swarm/certs/host1.local.pem"
echo "✓ Created host1.local.pem (4096-bit, 10 years)"
echo "  - $SCRIPT_DIR/static/host1.local.pem"
echo "  - $SCRIPT_DIR/swarm/certs/host1.local.pem"
echo ""

# ============================================================================
# Generate SSL Certificate for host2.local (2048-bit RSA, 1-year validity)
# ============================================================================
echo "Generating host2.local certificate (2048-bit RSA, 1-year validity)..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SCRIPT_DIR/docker/host2.local.pem" \
    -out "$SCRIPT_DIR/docker/host2.local.pem" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=host2.local"

# Copy to swarm directory
cp "$SCRIPT_DIR/docker/host2.local.pem" "$SCRIPT_DIR/swarm/certs/host2.local.pem"
echo "✓ Created host2.local.pem (2048-bit, 1 year)"
echo "  - $SCRIPT_DIR/docker/host2.local.pem"
echo "  - $SCRIPT_DIR/swarm/certs/host2.local.pem"
echo ""

# ============================================================================
# Generate JWT RSA Key Pair (2048-bit)
# ============================================================================
echo "Generating JWT RSA key pair (2048-bit)..."

# Generate private key
openssl genrsa -out "$SCRIPT_DIR/docker/jwt_private.pem" 2048

# Extract public key
openssl rsa -in "$SCRIPT_DIR/docker/jwt_private.pem" -pubout -out "$SCRIPT_DIR/docker/jwt_pubkey.pem"

echo "✓ Created JWT key pair (2048-bit)"
echo "  - $SCRIPT_DIR/docker/jwt_private.pem (private key)"
echo "  - $SCRIPT_DIR/docker/jwt_pubkey.pem (public key)"
echo ""

# ============================================================================
# Generate Placeholder Certificate
# ============================================================================
echo "Generating placeholder certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SCRIPT_DIR/docker/certs/haproxy/.place_holder_cert.pem" \
    -out "$SCRIPT_DIR/docker/certs/haproxy/.place_holder_cert.pem" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=placeholder"

echo "✓ Created placeholder certificate"
echo "  - $SCRIPT_DIR/docker/certs/haproxy/.place_holder_cert.pem"
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