#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/bump-version.sh <new-version>
  scripts/bump-version.sh --verify <new-version>
  scripts/bump-version.sh --current

Description:
  Updates all version references (images, docs, Helm chart) to <new-version>
  and bumps the Helm chart version patch. Use --verify to check the repo is
  already updated for <new-version> (no changes are made). Use --current to
  display the current versions.
EOF
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART_FILE="$REPO_ROOT/helm/easyhaproxy/Chart.yaml"

# Handle --current flag
if [[ "${1:-}" == "--current" ]]; then
  if [[ ! -f "$CHART_FILE" ]]; then
    echo "Error: Chart file not found at $CHART_FILE"
    exit 1
  fi
  CURRENT_APP_VERSION=$(grep 'appVersion:' "$CHART_FILE" | head -1 | awk -F'"' '{print $2}')
  CURRENT_CHART_VERSION=$(grep '^version:' "$CHART_FILE" | head -1 | awk '{print $2}')
  CURRENT_PYPROJECT_VERSION=$(grep '^version = ' "$REPO_ROOT/pyproject.toml" | head -1 | awk -F'"' '{print $2}')
  echo "Current versions:"
  echo "  App Version:       $CURRENT_APP_VERSION"
  echo "  Chart Version:     $CURRENT_CHART_VERSION"
  echo "  pyproject.toml:    $CURRENT_PYPROJECT_VERSION"
  exit 0
fi

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

# Extract base version (strip pre-release suffix for RELEASE.md check)
# Examples: 5.1.0-beta.1 -> 5.1.0, 5.1.0b1 -> 5.1.0, 5.1.0 -> 5.1.0
BASE_VERSION=$(echo "$NEW_VERSION" | sed -E 's/^([0-9]+\.[0-9]+\.[0-9]+).*/\1/')

# Check if base version exists in RELEASE.md Version History
if ! grep -q "| $BASE_VERSION " "$REPO_ROOT/RELEASE.md"; then
  echo "❌ Error: Version $BASE_VERSION not found in RELEASE.md Version History table."
  echo ""
  echo "Please manually add an entry for version $BASE_VERSION to RELEASE.md before running this script."
  echo "Add a row to the Version History table like:"
  echo ""
  echo "| $BASE_VERSION   | YYYY-MM-DD   | Major/Minor/Patch | Brief description of changes |"
  echo ""
  exit 1
fi

cd "$REPO_ROOT"
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
  check_contains "version = \"$NEW_VERSION\"" pyproject.toml "pyproject.toml version"

  if grep -R "byjg/easy-haproxy:" tests_e2e | grep -v "$NEW_VERSION" >/dev/null; then
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

# Update pyproject.toml
sed -i "s#^version = \"[a-zA-Z0-9\\.-]*\"#version = \"$NEW_VERSION\"#g" pyproject.toml

# Update Helm appVersion
sed -i "s#appVersion: \"[a-zA-Z0-9\\.-]*\"#appVersion: \"$NEW_VERSION\"#g" "$CHART_FILE"

# Update examples
find tests_e2e -type f -name '*.yml' -exec sed -i "s#\\(byjg/easy-haproxy:\\)[a-zA-Z0-9\\.-]*#\\1$NEW_VERSION#g" {} \; -print
# Update raw GitHub URLs in Kubernetes examples
find tests_e2e/kubernetes -type f -name '*.yml' -exec sed -i "s#raw.githubusercontent.com/byjg/docker-easy-haproxy/[a-zA-Z0-9\\.\\-]*/deploy/kubernetes/easyhaproxy-daemonset.yml#raw.githubusercontent.com/byjg/docker-easy-haproxy/$NEW_VERSION/deploy/kubernetes/easyhaproxy-daemonset.yml#g" {} \;

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
echo "  5) After merge: git checkout master && git pull"
echo "  6) git tag -a $NEW_VERSION -m \"Release $NEW_VERSION\""
echo "  7) git push origin $NEW_VERSION"
