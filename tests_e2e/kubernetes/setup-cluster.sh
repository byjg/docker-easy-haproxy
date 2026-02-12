#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

CLUSTER_NAME="easyhaproxy-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/.kind"
KIND_BIN="${BIN_DIR}/kind"
KUBECTL_BIN="${BIN_DIR}/kubectl"
HELM_BIN="${BIN_DIR}/helm"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Port configuration (matches test_kubernetes.py)
HTTP_PORT=10080
HTTPS_PORT=10443
STATS_PORT=11936

echo -e "${BLUE}[1/9] Setting up kind cluster '${CLUSTER_NAME}'...${NC}"

# Ensure kind is installed
if [ ! -f "${KIND_BIN}" ]; then
    echo "Installing kind locally..."
    mkdir -p "${BIN_DIR}"
    curl -Lo "${KIND_BIN}" "https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64"
    chmod +x "${KIND_BIN}"
    echo -e "${GREEN}✓ kind installed to ${KIND_BIN}${NC}"
fi

# Ensure kubectl is installed
if ! command -v kubectl &> /dev/null; then
    if [ ! -f "${KUBECTL_BIN}" ]; then
        echo "Installing kubectl locally..."
        mkdir -p "${BIN_DIR}"
        VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
        curl -Lo "${KUBECTL_BIN}" "https://dl.k8s.io/release/${VERSION}/bin/linux/amd64/kubectl"
        chmod +x "${KUBECTL_BIN}"
        echo -e "${GREEN}✓ kubectl installed to ${KUBECTL_BIN}${NC}"
    fi
    KUBECTL="${KUBECTL_BIN}"
else
    KUBECTL="kubectl"
fi

# Ensure helm is installed
if ! command -v helm &> /dev/null; then
    if [ ! -f "${HELM_BIN}" ]; then
        echo "Installing helm locally..."
        mkdir -p "${BIN_DIR}"
        HELM_VERSION="v3.13.3"
        HELM_TAR="${BIN_DIR}/helm.tar.gz"
        curl -Lo "${HELM_TAR}" "https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz"
        tar -xzf "${HELM_TAR}" -C "${BIN_DIR}" --strip-components=1 linux-amd64/helm
        rm "${HELM_TAR}"
        chmod +x "${HELM_BIN}"
        echo -e "${GREEN}✓ helm installed to ${HELM_BIN}${NC}"
    fi
    HELM="${HELM_BIN}"
else
    HELM="helm"
fi

# Check if cluster already exists
echo -e "${BLUE}[1/9] Checking for existing cluster...${NC}"
if ${KIND_BIN} get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${BLUE}Cluster '${CLUSTER_NAME}' already exists, deleting it first...${NC}"
    ${KIND_BIN} delete cluster --name "${CLUSTER_NAME}"
fi

# Create cluster config
echo -e "${BLUE}[1/9] Writing cluster config...${NC}"
CLUSTER_CONFIG="${BIN_DIR}/cluster-config.yaml"
mkdir -p "${BIN_DIR}"
cat > "${CLUSTER_CONFIG}" <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 80
    hostPort: ${HTTP_PORT}
    protocol: TCP
  - containerPort: 443
    hostPort: ${HTTPS_PORT}
    protocol: TCP
  - containerPort: 1936
    hostPort: ${STATS_PORT}
    protocol: TCP
EOF

# Create cluster
echo -e "${BLUE}[2/9] Creating kind cluster (this may take 1-2 minutes)...${NC}"
${KIND_BIN} create cluster --name "${CLUSTER_NAME}" --config "${CLUSTER_CONFIG}"

# Set kubectl context
echo -e "${BLUE}[3/9] Setting kubectl context...${NC}"
${KUBECTL} config use-context "kind-${CLUSTER_NAME}"

# Wait for nodes to be ready
echo -e "${BLUE}[3/9] Waiting for cluster nodes to be ready...${NC}"
${KUBECTL} wait --for=condition=Ready nodes --all --timeout=30s

echo -e "${GREEN}✓ kind cluster '${CLUSTER_NAME}' is ready${NC}"

# Build and load local EasyHAProxy image
echo -e "${BLUE}[4/9] Building local EasyHAProxy image (may take 30-60s)...${NC}"
docker build -t byjg/easy-haproxy:local \
    -f "${PROJECT_ROOT}/build/Dockerfile" \
    "${PROJECT_ROOT}"

echo -e "${BLUE}[5/9] Loading image into kind cluster (may take 10-20s)...${NC}"
${KIND_BIN} load docker-image byjg/easy-haproxy:local --name "${CLUSTER_NAME}"

# Generate EasyHAProxy manifest using Helm
echo -e "${BLUE}[6/9] Generating EasyHAProxy manifest from Helm...${NC}"
HELM_DIR="${PROJECT_ROOT}/helm"
MANIFEST_PATH="${BIN_DIR}/easyhaproxy-local.yml"

${HELM} template ingress "${HELM_DIR}/easyhaproxy" \
    --namespace easyhaproxy \
    --set service.create=false \
    --set image.tag=local \
    --set image.pullPolicy=Never \
    > "${MANIFEST_PATH}"

# Install EasyHAProxy
echo -e "${BLUE}[7/9] Creating easyhaproxy namespace...${NC}"
${KUBECTL} create namespace easyhaproxy

echo -e "${BLUE}[7/9] Applying EasyHAProxy manifest...${NC}"
${KUBECTL} apply -f "${MANIFEST_PATH}"

# Label the control-plane node
echo -e "${BLUE}[8/9] Labeling control-plane node...${NC}"
${KUBECTL} label nodes "${CLUSTER_NAME}-control-plane" \
    "easyhaproxy/node=master" --overwrite

# Wait for EasyHAProxy to be ready
echo -e "${BLUE}[9/9] Waiting for EasyHAProxy pods to be ready...${NC}"
if ${KUBECTL} wait --for=condition=Ready pods \
    -n easyhaproxy -l "app.kubernetes.io/name=easyhaproxy" \
    --timeout=30s 2>/dev/null; then
    echo -e "${GREEN}✓ EasyHAProxy pods are ready${NC}"
else
    echo -e "${RED}✗ Pods not ready within 30s. Checking status...${NC}"
    ${KUBECTL} get pods -n easyhaproxy -o wide
    echo -e "\n${BLUE}Events:${NC}"
    ${KUBECTL} get events -n easyhaproxy --sort-by=.lastTimestamp
    exit 1
fi

echo -e "${GREEN}✓ All setup complete! Cluster is ready.${NC}"
echo ""
echo -e "${BLUE}Cluster Information:${NC}"
echo -e "  Cluster name: ${CLUSTER_NAME}"
echo -e "  HTTP port:    localhost:${HTTP_PORT}"
echo -e "  HTTPS port:   localhost:${HTTPS_PORT}"
echo -e "  Stats port:   localhost:${STATS_PORT}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  Apply example ingress:     ${KUBECTL} apply -f ${SCRIPT_DIR}/service.yml"
echo -e "  Check EasyHAProxy logs:    ${KUBECTL} logs -n easyhaproxy -l app.kubernetes.io/name=easyhaproxy -f"
echo -e "  Test with curl:            curl -H 'Host: example.org' http://localhost:${HTTP_PORT}"
echo -e "  Delete cluster:            ${SCRIPT_DIR}/teardown-cluster.sh"
echo ""