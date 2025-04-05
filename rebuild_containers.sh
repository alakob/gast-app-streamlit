#!/bin/bash
# Script to rebuild and restart containers with the proper dependencies for real-time updates

echo "=== AMR Predictor - Rebuilding Containers ==="
echo "This script will rebuild the API and Streamlit containers with all required dependencies"

# Enable Docker Compose Bake for better build performance
export COMPOSE_BAKE=true
echo "Enabled Compose Bake for improved build performance"

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down

# Build containers with no cache to ensure fresh dependencies
echo "Rebuilding containers (this may take a few minutes)..."
docker-compose build --no-cache amr-api streamlit

# Start the containers
echo "Starting containers..."
docker-compose up -d

# Show logs to verify successful startup
echo "Displaying logs to verify startup..."
docker-compose logs -f
