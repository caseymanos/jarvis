# Local Testing Guide

This guide explains how to test the Jarvis backend locally before deploying to production.

## Prerequisites

- Docker Desktop installed and running
- At least 4GB RAM available for Docker
- Ports 5432, 6379, 7233, 8000, 8233 available

## Quick Start

### Option 1: Automated Testing (Recommended)

```bash
cd backend
./test-local.sh
```

This script will:
1. Start all services (PostgreSQL, Redis, Temporal, Backend)
2. Wait for services to be healthy
3. Run basic endpoint tests
4. Display service URLs and logs
5. Keep services running for manual testing

### Option 2: Manual Testing

```bash
cd backend

# Start all services
docker-compose up -d

# Watch logs
docker-compose logs -f backend

# Stop services when done
docker-compose down
```

## What Gets Tested

The test script validates:
- ✅ Root endpoint (`/`)
- ✅ Health endpoint (`/health`)
- ✅ Retrieval endpoint (`/retrieval/search`)
- ✅ All dependent services (Postgres, Redis, Temporal)

## Service URLs

Once running, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| Backend API | http://localhost:8000 | Main API |
| API Docs | http://localhost:8000/docs | Interactive Swagger docs |
| Health Check | http://localhost:8000/health | Service health status |
| Temporal UI | http://localhost:8233 | Workflow monitoring |

## Database Access

Connect to the local PostgreSQL database:

```bash
# Using psql
psql postgresql://jarvisadmin:JarvisLocalDev2024@localhost:5432/jarvis

# Using Docker exec
docker exec -it jarvis-postgres-local psql -U jarvisadmin -d jarvis
```

## Redis Access

Connect to the local Redis instance:

```bash
# Using redis-cli via Docker
docker exec -it jarvis-redis-local redis-cli

# Test commands
redis-cli -h localhost -p 6379 ping
```

## Testing the API

### Using curl

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test retrieval search
curl -X POST http://localhost:8000/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5}'

# Test mission notes
curl -X POST http://localhost:8000/missions/note \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session", "content": "Test note"}'
```

### Using the Interactive API Docs

1. Open http://localhost:8000/docs in your browser
2. Explore available endpoints
3. Try out requests directly in the browser

## Troubleshooting

### Services Won't Start

```bash
# Check if ports are already in use
lsof -i :8000
lsof -i :5432
lsof -i :6379

# View service status
docker-compose ps

# View logs for specific service
docker-compose logs postgres
docker-compose logs redis
docker-compose logs temporal
docker-compose logs backend
```

### Backend Container Fails

```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# 1. Database not ready - wait a bit longer
# 2. Missing dependencies - rebuild image
docker-compose build --no-cache backend
docker-compose up -d
```

### Database Connection Issues

```bash
# Check if Postgres is healthy
docker-compose ps postgres

# Test database connection
docker exec -it jarvis-postgres-local pg_isready -U jarvisadmin

# View Postgres logs
docker-compose logs postgres
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Rebuild and restart
docker-compose up -d --build
```

## Architecture Validation

The docker-compose setup uses:
- `platform: linux/amd64` - Ensures AMD64 architecture (same as AWS ECS)
- Health checks for all services
- Proper service dependencies
- Environment variables matching production

This means if it works locally with docker-compose, it should work on AWS ECS.

## Differences from Production

| Feature | Local | Production (AWS) |
|---------|-------|------------------|
| Database | PostgreSQL in Docker | RDS PostgreSQL 16 |
| Redis | Redis in Docker | ElastiCache Redis |
| Temporal | Docker container | Would need AWS deployment |
| Backend | Docker on localhost | ECS Fargate |
| SSL/HTTPS | No | Yes (via ALB) |

## Next Steps After Local Testing

Once local testing passes:

1. **Frontend Testing**: Start the Next.js frontend and connect to local backend
2. **Production Deploy**: Push Docker image to ECR and deploy to ECS
3. **Integration Testing**: Test frontend + backend together
4. **Load Testing**: Test with realistic traffic patterns

## Clean Up

```bash
# Stop all services
docker-compose down

# Remove volumes (deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```
