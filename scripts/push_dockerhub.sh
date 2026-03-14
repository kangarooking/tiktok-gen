#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${1:-${DOCKERHUB_NAMESPACE:-}}"
TAG="${2:-${IMAGE_TAG:-latest}}"

if [[ -z "${NAMESPACE}" ]]; then
  echo "Usage: $0 <dockerhub_namespace> [tag]"
  echo "Example: $0 myname v1.0.0"
  exit 1
fi

BACKEND_LOCAL="tiktok-video-lab-backend:latest"
FRONTEND_LOCAL="tiktok-video-lab-frontend:latest"

BACKEND_REMOTE="${NAMESPACE}/tiktokgen-backend:${TAG}"
FRONTEND_REMOTE="${NAMESPACE}/tiktokgen-frontend:${TAG}"

echo "[1/4] Tag backend image -> ${BACKEND_REMOTE}"
docker tag "${BACKEND_LOCAL}" "${BACKEND_REMOTE}"

echo "[2/4] Tag frontend image -> ${FRONTEND_REMOTE}"
docker tag "${FRONTEND_LOCAL}" "${FRONTEND_REMOTE}"

echo "[3/4] Push backend"
docker push "${BACKEND_REMOTE}"

echo "[4/4] Push frontend"
docker push "${FRONTEND_REMOTE}"

echo "Done."
echo "Set DOCKERHUB_NAMESPACE=${NAMESPACE} and IMAGE_TAG=${TAG} in .env for deployment."
