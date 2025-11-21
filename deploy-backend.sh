#!/bin/bash
set -e

echo "🚀 Deploying Jarvis Backend to AWS EKS Fargate"

# Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID}"
CLUSTER_NAME="${CLUSTER_NAME:-jarvis-cluster}"
ECR_REPO="jarvis-backend"

# Check required environment variables
if [ -z "$AWS_ACCOUNT_ID" ]; then
  echo "❌ AWS_ACCOUNT_ID environment variable is required"
  exit 1
fi

# Build and push Docker image
echo "🐳 Building Docker image..."
cd backend
docker build -t ${ECR_REPO}:latest .

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Create ECR repository if it doesn't exist
echo "📦 Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${AWS_REGION} || \
  aws ecr create-repository --repository-name ${ECR_REPO} --region ${AWS_REGION}

# Tag and push image
echo "⬆️  Pushing image to ECR..."
docker tag ${ECR_REPO}:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:latest

# Update kubeconfig
echo "🔧 Updating kubeconfig..."
aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}

# Apply Kubernetes manifests
echo "☸️  Applying Kubernetes manifests..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml

# Apply secrets (requires manual setup first)
echo "⚠️  Ensure secrets are created before proceeding"
echo "   Run: kubectl create secret generic jarvis-secrets -n jarvis \\"
echo "        --from-literal=database-url=<DATABASE_URL> \\"
echo "        --from-literal=redis-url=<REDIS_URL>"

kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/jarvis-backend -n jarvis

echo "✅ Backend deployment complete!"
echo "📝 Check status: kubectl get pods -n jarvis"
echo "📝 View logs: kubectl logs -f deployment/jarvis-backend -n jarvis"
