#!/bin/bash
# Quick restart script for GLM configuration

echo "🔄 Restarting ccBot with GLM configuration..."

# Stop containers
docker-compose down

# Start containers
docker-compose up -d

# Wait for startup
sleep 5

# Check status
docker-compose ps
docker-compose logs --tail=20

echo ""
echo "✅ Restart complete. Check logs above for any errors."
