#!/bin/bash
set -e

echo "🔐 Setting up Kubernetes secrets for Jarvis"

# Configuration
NAMESPACE="jarvis"

# Check if namespace exists
if ! kubectl get namespace ${NAMESPACE} &> /dev/null; then
  echo "Creating namespace: ${NAMESPACE}"
  kubectl create namespace ${NAMESPACE}
fi

# Function to prompt for secret value
prompt_secret() {
  local secret_name=$1
  local prompt_text=$2
  local default_value=$3

  if [ -n "$default_value" ]; then
    read -p "${prompt_text} [${default_value}]: " value
    echo "${value:-$default_value}"
  else
    read -sp "${prompt_text}: " value
    echo ""
    echo "$value"
  fi
}

# Generate NextAuth secret
NEXTAUTH_SECRET=$(openssl rand -base64 32)
echo "✓ Generated NextAuth secret"

# Prompt for database URL
echo ""
DATABASE_URL=$(prompt_secret "database-url" "Enter DATABASE_URL" "postgresql://jarvis_user:password@localhost:5432/jarvis")

# Prompt for Redis URL
REDIS_URL=$(prompt_secret "redis-url" "Enter REDIS_URL" "redis://localhost:6379")

# Prompt for Azure AD credentials
echo ""
echo "Azure AD OAuth Configuration:"
AZURE_AD_CLIENT_ID=$(prompt_secret "azure-ad-client-id" "Enter Azure AD Client ID" "")
AZURE_AD_CLIENT_SECRET=$(prompt_secret "azure-ad-client-secret" "Enter Azure AD Client Secret" "")
AZURE_AD_TENANT_ID=$(prompt_secret "azure-ad-tenant-id" "Enter Azure AD Tenant ID" "")

# Create secrets
echo ""
echo "Creating Kubernetes secrets..."

kubectl create secret generic jarvis-secrets \
  --namespace=${NAMESPACE} \
  --from-literal=database-url="${DATABASE_URL}" \
  --from-literal=redis-url="${REDIS_URL}" \
  --from-literal=nextauth-secret="${NEXTAUTH_SECRET}" \
  --from-literal=azure-ad-client-id="${AZURE_AD_CLIENT_ID}" \
  --from-literal=azure-ad-client-secret="${AZURE_AD_CLIENT_SECRET}" \
  --from-literal=azure-ad-tenant-id="${AZURE_AD_TENANT_ID}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "✅ Secrets created successfully!"

# Apply ConfigMap
echo "Applying ConfigMap..."
kubectl apply -f secrets-template.yaml

echo "✅ Configuration complete!"
echo "📝 Verify: kubectl get secrets -n ${NAMESPACE}"
