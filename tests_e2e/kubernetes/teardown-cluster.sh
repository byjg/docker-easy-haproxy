#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CLUSTER_NAME="easyhaproxy-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/.kind"
KIND_BIN="${BIN_DIR}/kind"

# Check if kind binary exists
if [ ! -f "${KIND_BIN}" ]; then
    # Try to use system kind
    if command -v kind &> /dev/null; then
        KIND_BIN="kind"
    else
        echo -e "${RED}✗ kind binary not found. Cannot delete cluster.${NC}"
        echo "  Cluster may not exist or kind is not installed."
        exit 1
    fi
fi

# Check if cluster exists
if ! ${KIND_BIN} get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${BLUE}Cluster '${CLUSTER_NAME}' does not exist. Nothing to delete.${NC}"
    exit 0
fi

echo -e "${BLUE}Deleting kind cluster '${CLUSTER_NAME}'...${NC}"

if ${KIND_BIN} delete cluster --name "${CLUSTER_NAME}"; then
    echo -e "${GREEN}✓ Cluster deleted successfully${NC}"
else
    echo -e "${RED}✗ Failed to delete cluster${NC}"
    exit 1
fi