#!/bin/sh
set -e

# Create secrets dir if not exists (will be owned by root initially)
mkdir -p /secrets

if [ -n "$VERTEX_AI" ]; then
  printf '%s' "$VERTEX_AI" > /secrets/vertex_ai.json
  chmod 600 /secrets/vertex_ai.json
  export VERTEX_AI_CREDENTIALS=/secrets/vertex_ai.json
fi

# Execute the main command (passed as CMD in the Dockerfile)
exec "$@"


# set -x VERTEX_AI_CREDENTIALS (pwd)/vertex_ai.json;
# set -x GOOGLE_APPLICATION_CREDENTIALS (pwd)/cloud_vision.json;
# set -x SERVICE_ACCOUNT_CREDENTIALS (pwd)/service_account.json