#!/bin/sh
set -e

# Create secrets dir if not exists (will be owned by root initially)
mkdir -p /secrets

# If secrets are provided as environment variables (Cloud Run --set-secrets),
# write them to files and export the expected env var paths for Google clients.
if [ -n "$CLOUD_VISION" ]; then
  printf '%s' "$CLOUD_VISION" > /secrets/cloud_vision.json
  chmod 600 /secrets/cloud_vision.json
  export GOOGLE_APPLICATION_CREDENTIALS=/secrets/cloud_vision.json
fi

if [ -n "$VERTEX_AI" ]; then
  printf '%s' "$VERTEX_AI" > /secrets/vertex_ai.json
  chmod 600 /secrets/vertex_ai.json
  export VERTEX_AI_CREDENTIALS=/secrets/vertex_ai.json
fi

# Execute the main command (passed as CMD in the Dockerfile)
exec "$@"
