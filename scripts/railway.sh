#!/bin/bash

# Define services
SERVICES=("python-saas-template")

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Please install it first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo ".env file not found!"
    exit 1
fi

# Read .env file and set variables for each service
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    if [[ -z "$key" || "$key" == \#* ]]; then
        continue
    fi

    # Trim whitespace
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)

    # Set variables for each service
    for service in "${SERVICES[@]}"; do
        echo "Setting $key for $service..."
        railway variables --service "$service" --set "$key=$value"
    done
done < .env

echo "Environment variables set for services: ${SERVICES[*]}"