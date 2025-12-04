#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/bump-version.sh <new-version>
  scripts/bump-version.sh --verify <new-version>

Description:
  Updates all version references (images, docs, Helm chart) to <new-version>
  and bumps the Helm chart version patch. Use --verify to check the repo is
  already updated for <new-version> (no changes are made).
EOF
}

MODE="apply"
if [[ "${1:-}" == "--verify" ]]; then
  MODE="verify"
  shift
fi

NEW_VERSION="${1:-}"
if [[ -z "$NEW_VERSION" ]]; then
  usage
  exit 1
fi

if [[ "$NEW_VERSION" == "latest" ]]; then
  echo "Skipping 'latest' tag."
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CHART_FILE="helm/easyhaproxy/Chart.yaml"
CURRENT_APP_VERSION=$(grep 'appVersion:' "$CHART_FILE" | head -1 | awk -F'"' '{print $2}')
CURRENT_CHART_VERSION_RAW=$(grep '^version:' "$CHART_FILE" | head -1 | awk '{print $2}')
# Normalize chart version (strip trailing dots/spaces)
CURRENT_CHART_VERSION="${CURRENT_CHART_VERSION_RAW%%.}"

if [[ "$MODE" == "verify" ]]; then
  echo "Verifying repository is prepared for version $NEW_VERSION..."
  STATUS=0

  check_contains() {
    local pattern="$1" file="$2" note="$3"
    if ! grep -q "$pattern" "$file"; then
      echo "❌ $note ($file)"
      STATUS=1
    else
      echo "✅ $note ($file)"
    fi
  }

  check_contains "appVersion: \"$NEW_VERSION\"" "$CHART_FILE" "Chart appVersion"
  check_contains "version: \"$NEW_VERSION\"" deploy/kubernetes/easyhaproxy-daemonset.yml "K8s daemonset manifest version"
  check_contains "easy-haproxy:$NEW_VERSION" deploy/kubernetes/easyhaproxy-daemonset.yml "K8s daemonset image tag"
  check_contains "easy-haproxy:$NEW_VERSION" deploy/docker/docker-compose.yml "Docker compose image tag"

  if grep -R "byjg/easy-haproxy:" examples | grep -v "$NEW_VERSION" >/dev/null; then
    echo "❌ Examples still reference a different tag. Run bump-version.sh to update."
    STATUS=1
  else
    echo "✅ Examples reference $NEW_VERSION"
  fi

  exit $STATUS
fi

echo "Updating repository to version $NEW_VERSION (previous appVersion: $CURRENT_APP_VERSION, chart version: $CURRENT_CHART_VERSION)"

# Update deployment manifests and docs
sed -i "s#easy-haproxy:[a-zA-Z0-9\\.-]*#easy-haproxy:$NEW_VERSION#g" deploy/docker/docker-compose.yml
sed -i "s#version: \"[a-zA-Z0-9\\.-]*\"#version: \"$NEW_VERSION\"#g" deploy/kubernetes/easyhaproxy-*.yml
sed -i "s#easy-haproxy:[a-zA-Z0-9\\.-]*#easy-haproxy:$NEW_VERSION#g" deploy/kubernetes/easyhaproxy-*.yml
sed -i "s#easy-haproxy/[a-zA-Z0-9\\.-]*/#easy-haproxy/$NEW_VERSION/#g" docs/kubernetes.md
sed -i "s#easy-haproxy:[a-zA-Z0-9\\.-]*#easy-haproxy:$NEW_VERSION#g" docs/swarm.md
sed -i "s/^\\*\\*Current Version:\\*\\* \`[^\`]*\`/**Current Version:** \`$NEW_VERSION\`/" RELEASE.md
sed -i "s/^\\*\\*App Version:\\*\\* \`[^\`]*\`/**App Version:** \`$NEW_VERSION\`/" RELEASE.md

# Update Helm appVersion
sed -i "s#appVersion: \"[a-zA-Z0-9\\.-]*\"#appVersion: \"$NEW_VERSION\"#g" "$CHART_FILE"

# Update examples
find examples -type f -name '*.yml' -exec sed -i "s#\\(byjg/easy-haproxy:\\)[a-zA-Z0-9\\.-]*#\\1$NEW_VERSION#g" {} \; -print
# Update raw GitHub URLs in Kubernetes examples
find examples/kubernetes -type f -name '*.yml' -exec sed -i "s#raw.githubusercontent.com/byjg/docker-easy-haproxy/[0-9\\.\\-]*/deploy/kubernetes/easyhaproxy-daemonset.yml#raw.githubusercontent.com/byjg/docker-easy-haproxy/$NEW_VERSION/deploy/kubernetes/easyhaproxy-daemonset.yml#g" {} \;

# Bump chart version (patch)
SANITIZED_CHART_VERSION="${CURRENT_CHART_VERSION%\.}"
IFS='.' read -r -a _parts <<< "$SANITIZED_CHART_VERSION"
if [[ "${#_parts[@]}" -lt 1 ]] || ! [[ "${_parts[-1]}" =~ ^[0-9]+$ ]]; then
  echo "Invalid chart version '$CURRENT_CHART_VERSION'"
  exit 1
fi
last_index=$((${#_parts[@]} - 1))
_parts[$last_index]=$(( ${_parts[$last_index]} + 1 ))
NEXT_CHART_VERSION=$(IFS='.'; echo "${_parts[*]}")
sed -i -E "s/^version: .*/version: $NEXT_CHART_VERSION/" "$CHART_FILE"
sed -i -E "s/helm\\.sh\\/chart: easyhaproxy-[0-9\\.]+/helm.sh\\/chart: easyhaproxy-$NEXT_CHART_VERSION/" deploy/kubernetes/easyhaproxy-*.yml

echo "Done. Updated appVersion to $NEW_VERSION and chart version to $NEXT_CHART_VERSION."
echo "Next steps:"
echo "  1) git status (review changes)"
echo "  2) git add ."
echo "  3) git commit -m \"Bump version to $NEW_VERSION (chart $NEXT_CHART_VERSION)\""
echo "  4) Open a PR to master and merge via PR."
