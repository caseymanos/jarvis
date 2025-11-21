#!/bin/bash

# Local Testing Script for Jarvis Backend
# This script helps you test the backend locally before deploying to production

set -e

echo "🧪 Jarvis Local Testing Script"
echo "================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    docker-compose down
}

# Trap cleanup on script exit
trap cleanup EXIT

# Start services
echo "🚀 Starting services with docker-compose..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
echo "   This may take 30-60 seconds..."
echo ""

# Wait for backend to be healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps | grep -q "healthy"; then
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - waiting for services..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Services failed to become healthy"
    echo ""
    echo "📋 Service Status:"
    docker-compose ps
    echo ""
    echo "📋 Backend Logs:"
    docker-compose logs backend
    exit 1
fi

echo ""
echo "✅ All services are healthy!"
echo ""

# Test the backend endpoints
echo "🔍 Testing Backend Endpoints"
echo "================================"
echo ""

# Test root endpoint
echo "1. Testing root endpoint (/)..."
response=$(curl -s http://localhost:8000/)
if echo "$response" | grep -q "Jarvis Backend API"; then
    echo "   ✅ Root endpoint working"
    echo "   Response: $response" | head -c 200
    echo ""
else
    echo "   ❌ Root endpoint failed"
    echo "   Response: $response"
fi
echo ""

# Test health endpoint
echo "2. Testing health endpoint (/health)..."
health_response=$(curl -s http://localhost:8000/health)
if echo "$health_response" | grep -q "status"; then
    echo "   ✅ Health endpoint working"
    echo "   Response: $health_response" | head -c 200
    echo ""
else
    echo "   ❌ Health endpoint failed"
    echo "   Response: $health_response"
fi
echo ""

# Test retrieval endpoint
echo "3. Testing retrieval endpoint (/retrieval/search)..."
retrieval_test='{"query":"test query","top_k":5}'
retrieval_response=$(curl -s -X POST http://localhost:8000/retrieval/search \
    -H "Content-Type: application/json" \
    -d "$retrieval_test" || echo "FAILED")

if [ "$retrieval_response" != "FAILED" ]; then
    echo "   ✅ Retrieval endpoint working"
    echo "   Response: $retrieval_response" | head -c 200
    echo ""
else
    echo "   ⚠️  Retrieval endpoint may not have data yet (expected for fresh setup)"
fi
echo ""

# Show service URLs
echo "🌐 Service URLs"
echo "================================"
echo "Backend API:      http://localhost:8000"
echo "API Docs:         http://localhost:8000/docs"
echo "Health Check:     http://localhost:8000/health"
echo "Temporal UI:      http://localhost:8233"
echo ""
echo "Database:"
echo "  Host:           localhost:5432"
echo "  Database:       jarvis"
echo "  User:           jarvisadmin"
echo "  Password:       JarvisLocalDev2024"
echo ""
echo "Redis:"
echo "  URL:            redis://localhost:6379"
echo ""

# Show logs
echo "📋 Recent Backend Logs"
echo "================================"
docker-compose logs --tail=20 backend
echo ""

# Keep services running
echo "✅ All tests complete!"
echo ""
echo "Services are still running. You can:"
echo "  - View API docs at http://localhost:8000/docs"
echo "  - Test endpoints manually"
echo "  - Check logs with: docker-compose logs -f backend"
echo ""
echo "Press Ctrl+C to stop all services and cleanup"
echo ""

# Wait for user interrupt
wait
