# EasyHAProxy Release Guide

This guide explains how to create a new release of EasyHAProxy, including Docker images, Helm charts, and documentation updates.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Release Process](#release-process)
- [Automated Release (Recommended)](#automated-release-recommended)
- [Manual Release](#manual-release)
- [Helm Chart Release](#helm-chart-release)
- [Post-Release Checklist](#post-release-checklist)
- [Troubleshooting](#troubleshooting)

## Overview

The EasyHAProxy release process uses GitHub Actions to automatically:
- Run tests
- Build multi-architecture Docker images (amd64, arm64)
- Publish Docker images to Docker Hub
- Update Helm chart versions
- Publish Helm charts
- Update documentation

## Prerequisites

Before creating a release, ensure you have:

1. **Permissions:**
   - Write access to the GitHub repository
   - Docker Hub credentials (for maintainers)
   - Access to GitHub secrets (for CI/CD)

2. **Local Setup:**
   - Git configured with your credentials
   - Docker installed (for local testing)
   - Python 3.x with pytest (for running tests)

3. **Repository Secrets (for maintainers):**
   - `DOCKER_REGISTRY`: Docker Hub registry URL
   - `DOCKER_REGISTRY_USER`: Docker Hub username
   - `DOCKER_REGISTRY_TOKEN`: Docker Hub access token
   - `DOC_TOKEN`: GitHub token for documentation updates

## Release Process

### Version Numbering

EasyHAProxy follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `4.6.0`)
  - **MAJOR**: Breaking changes or major architectural updates
  - **MINOR**: New features, plugin additions, backward-compatible changes
  - **PATCH**: Bug fixes, documentation updates, minor improvements

**Current Version:** `4.6.0` (as of Chart.yaml)

## Automated Release (Recommended)

The automated release process is triggered by pushing a semantic version tag.

### Step 1: Prepare the Release

1. **Ensure all changes are committed and pushed:**
   ```bash
   git status
   git add .
   git commit -m "Prepare release X.Y.Z"
   git push origin master
   ```

2. **Run tests locally:**
   ```bash
   cd src/
   pytest tests/ -vv
   ```

3. **Build and test Docker image locally:**
   ```bash
   make build
   # Or manually:
   docker build -t byjg/easy-haproxy:local -f build/Dockerfile .
   ```

### Step 2: Bump Versions (script + PR)

1. **Run the bump script from the repo root:**
   ```bash
   ./scripts/bump-version.sh 5.0.0
   ```
   This updates image tags, docs, Helm chart `appVersion`, and bumps the chart version patch.

2. **Review and commit the changes on a branch:**
   ```bash
   git status
   git add .
   git commit -m "Bump version to 5.0.0"
   git push origin <your-branch>
   ```

3. **Open a PR to `master` and merge it.** Branch protection requires merging through a PR; CI/CD no longer pushes directly.

4. **Tag from `master` after the PR merges:**
   ```bash
   git checkout master
   git pull
   git tag 5.0.0
   git push origin 5.0.0
   ```

### Step 3: What Happens Automatically

When you push a semantic version tag, GitHub Actions will:

1. **Run Tests** (`Test` job):
   - Install Python dependencies
   - Run pytest on all tests

2. **Build Multi-Arch Docker Images** (`Build` job):
   - Build for `linux/amd64` and `linux/arm64`
   - Tag image with version number (e.g., `byjg/easy-haproxy:4.7.0`)
   - Push to Docker Hub

3. **Verify Versions** (`Helm` job):
   - Ensures the repository already contains the tag version via `./scripts/bump-version.sh --verify <tag>`
   - Fails fast if the repo was not prepared before tagging (no auto-commits)

4. **Publish Helm Chart** (`HelmDeploy` job):
   - Package Helm chart
   - Publish to Helm repository at https://opensource.byjg.com/helm/

5. **Update Documentation** (`Documentation` job):
   - Publish documentation updates

### Step 4: Verify the Release

1. **Check Docker Hub:**
   ```bash
   docker pull byjg/easy-haproxy:4.7.0
   docker images | grep easy-haproxy
   ```

2. **Verify Helm chart:**
   ```bash
   helm repo add byjg https://opensource.byjg.com/helm
   helm repo update
   helm search repo easyhaproxy
   ```

3. **Create GitHub Release:**
   - Go to: https://github.com/byjg/docker-easy-haproxy/releases/new
   - Select the tag you created
   - Generate release notes
   - Add highlights of changes
   - Publish release

## Manual Release

For emergency releases or when CI/CD is unavailable.

### Manual Docker Build (Multi-Arch)

1. **Set up environment:**
   ```bash
   export DOCKER_USERNAME=your-username
   export DOCKER_PASSWORD=your-token
   export DOCKER_REGISTRY=docker.io
   export VERSIONS="4.7.0"
   ```

2. **Run multi-arch build:**
   ```bash
   ./build-multiarch.sh
   ```

   This script uses `buildah` and `podman` to create multi-architecture images.

### Manual Helm Chart Update

1. **Update Chart.yaml:**
   ```bash
   cd helm/easyhaproxy/

   # Update appVersion
   sed -i 's/appVersion: ".*"/appVersion: "4.7.0"/' Chart.yaml

   # Increment chart version
   # From: version: 0.1.9
   # To:   version: 0.1.10
   nano Chart.yaml
   ```

2. **Package and publish Helm chart:**
   ```bash
   helm package helm/easyhaproxy/
   # Follow your Helm repository's publishing process
   ```

## Helm Chart Release

The Helm chart version is automatically managed by CI/CD, but you can manually control it:

### Helm Chart Version Strategy

- **Chart version** (`version` in Chart.yaml):
  - Auto-incremented by CI/CD (patch version)
  - Format: `0.1.X` where X increments with each Docker release
  - Manual override: Edit Chart.yaml before tagging

- **App version** (`appVersion` in Chart.yaml):
  - Set to Docker image version (e.g., `4.7.0`)
  - Automatically updated by CI/CD

### Current Helm Chart

- **Chart Version:** `0.1.9`
- **App Version:** `4.6.0`
- **Repository:** https://opensource.byjg.com/helm/

## Post-Release Checklist

After a successful release:

- [ ] Verify Docker image on Docker Hub
- [ ] Test Docker image: `docker run byjg/easy-haproxy:X.Y.Z --version`
- [ ] Verify Helm chart availability
- [ ] Test Helm installation
- [ ] Create GitHub Release with changelog
- [ ] Update project README if needed
- [ ] Announce release (if major/minor)
- [ ] Update dependent projects (if applicable)

## Troubleshooting

### Build Fails

**Problem:** GitHub Actions build job fails

**Solutions:**
1. Check test output in GitHub Actions logs
2. Run tests locally: `cd src/ && pytest tests/ -vv`
3. Fix failing tests and push changes
4. Delete and recreate tag:
   ```bash
   git tag -d 4.7.0
   git push origin :refs/tags/4.7.0
   git tag 4.7.0
   git push origin 4.7.0
   ```

### Docker Push Fails

**Problem:** Cannot push to Docker Hub

**Solutions:**
1. Verify Docker Hub credentials in GitHub secrets
2. Check Docker Hub token permissions
3. Ensure image name matches: `byjg/easy-haproxy`

### Helm Chart Not Published

**Problem:** Helm chart doesn't appear in repository

**Solutions:**
1. Check `HelmDeploy` job logs in GitHub Actions
2. Verify `DOC_TOKEN` secret is valid
3. Wait a few minutes for chart to propagate
4. Clear Helm cache: `helm repo update`

### Version Not Updated

**Problem:** Version references not updated in docs/examples

**Solutions:**
1. Check `Helm` job logs for sed command errors
2. Verify commit was pushed with `[skip ci]` message
3. Manually update version references if needed:
   ```bash
   find examples -type f -name '*.yml' -exec sed -i "s/\(byjg\/easy-haproxy:\)[0-9\.]*/\1X.Y.Z/g" {} \;
   ```

### Multi-Arch Build Issues

**Problem:** ARM64 build fails

**Solutions:**
1. Verify QEMU is set up in GitHub Actions
2. Check build logs for architecture-specific errors
3. Test locally with Docker Buildx:
   ```bash
   docker buildx create --use
   docker buildx build --platform linux/amd64,linux/arm64 -t test .
   ```

## Quick Reference

### Commands

```bash
# Local build
make build

# Run tests
cd src/ && pytest tests/ -vv

# Create release tag
git tag 4.7.0 && git push origin 4.7.0

# Pull specific version
docker pull byjg/easy-haproxy:4.7.0

# Install Helm chart
helm install easyhaproxy byjg/easyhaproxy --version 0.1.10

# Check Helm chart info
helm show chart byjg/easyhaproxy
```

### Important URLs

- **GitHub Repository:** https://github.com/byjg/docker-easy-haproxy
- **Docker Hub:** https://hub.docker.com/r/byjg/easy-haproxy
- **Helm Repository:** https://opensource.byjg.com/helm/
- **Documentation:** https://opensource.byjg.com/devops/docker-easy-haproxy/
- **GitHub Actions:** https://github.com/byjg/docker-easy-haproxy/actions

### Version History

| Version | Release Date | Type | Highlights |
|---------|-------------|------|------------|
| 4.6.0   | 2024-11-27  | Minor | FastCGI plugin, JWT enhancements |
| 4.5.0   | 2024-XX-XX  | Minor | Previous release |
| ...     | ...         | ...   | ... |

---

**Need Help?**
- Open an issue: https://github.com/byjg/docker-easy-haproxy/issues
- Check documentation: https://opensource.byjg.com/devops/docker-easy-haproxy/
