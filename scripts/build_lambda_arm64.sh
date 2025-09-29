#!/bin/bash

# Build AWS Lambda deployment package for ARM64 (Python 3.13)
# - Installs dependencies from requirements.txt in a Lambda ARM64 container
# - Packages site-packages + project source into dist/lambda_arm64.zip

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
ok() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUILD_DIR="${ROOT_DIR}/.build_arm64"
DOCKER_IMAGE="public.ecr.aws/lambda/python:3.13-arm64"

cleanup() {
  rm -rf "${BUILD_DIR}" || true
}
trap cleanup EXIT

info "Building Lambda package (ARM64) from ${ROOT_DIR}"

# Validate prerequisites
if ! command -v docker >/dev/null 2>&1; then
  err "Docker is required. Please install and start Docker Desktop."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  err "Docker is not running. Start Docker and retry."
  exit 1
fi

if [ ! -f "${ROOT_DIR}/requirements.txt" ]; then
  err "requirements.txt not found in ${ROOT_DIR}"
  exit 1
fi

mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

# Copy project sources
cp -R "${ROOT_DIR}/lambda_function.py" "${BUILD_DIR}/"
cp -R "${ROOT_DIR}/aws_cloudwatch_mcp_adapter" "${BUILD_DIR}/aws_cloudwatch_mcp_adapter"
cp -R "${ROOT_DIR}/requirements.txt" "${BUILD_DIR}/requirements.txt"

info "Installing dependencies inside Lambda ARM64 container..."
docker run --rm \
  --platform linux/arm64 \
  --entrypoint="" \
  -v "${BUILD_DIR}:/var/task" \
  -w /var/task \
  "${DOCKER_IMAGE}" \
  /bin/bash -lc "pip install --no-cache-dir --upgrade --root-user-action=ignore -r requirements.txt -t ."

ok "Dependencies installed"

# Remove unnecessary artifacts
find "${BUILD_DIR}" -name "*.pyc" -delete || true
find "${BUILD_DIR}" -name "__pycache__" -type d -exec rm -rf {} + || true
find "${BUILD_DIR}" -name "*.dist-info" -type d -empty -delete || true

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ZIP_PATH="${DIST_DIR}/lambda_arm64_${TIMESTAMP}.zip"
rm -f "${ZIP_PATH}" || true

info "Creating deployment zip: ${ZIP_PATH}"
(
  cd "${BUILD_DIR}"
  zip -q -r "${ZIP_PATH}" . \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "*.egg-info/*" \
    -x ".git/*" \
    -x "tests/*" \
    -x "*.md" \
    -x ".DS_Store"
)

SIZE=$(du -h "${ZIP_PATH}" | cut -f1)
ok "Built ${ZIP_PATH} (${SIZE})"

echo
info "To deploy, upload ${ZIP_PATH} to your Lambda configured for architecture ARM64 and runtime Python 3.13."


