#!/bin/bash
set -e

# Check if the container is already running
if docker ps --format '{{.Names}}' | grep -q '^recipethis$'; then
  echo "Container is already running"
  exit 1
fi

docker build -t recipethis .

# put your various environment variables in a file named .env
docker run --restart=on-failure --env-file=.env recipethis
