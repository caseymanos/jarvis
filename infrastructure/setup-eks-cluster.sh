#!/bin/bash
set -e

echo "🏗️  Setting up AWS EKS Cluster with Fargate"

# Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
CLUSTER_NAME="${CLUSTER_NAME:-jarvis-cluster}"
K8S_VERSION="${K8S_VERSION:-1.28}"

# Check eksctl is installed
if ! command -v eksctl &> /dev/null; then
  echo "❌ eksctl is not installed. Please install it first:"
  echo "   brew install eksctl"
  exit 1
fi

# Create EKS cluster with Fargate
echo "🚀 Creating EKS cluster: ${CLUSTER_NAME}"
eksctl create cluster \
  --name ${CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --version ${K8S_VERSION} \
  --fargate

# Create Fargate profiles
echo "📋 Creating Fargate profiles..."
eksctl create fargateprofile \
  --cluster ${CLUSTER_NAME} \
  --region ${AWS_REGION} \
  --name jarvis-backend \
  --namespace jarvis

# Install AWS Load Balancer Controller
echo "⚖️  Installing AWS Load Balancer Controller..."

# Create IAM OIDC provider
eksctl utils associate-iam-oidc-provider \
  --region ${AWS_REGION} \
  --cluster ${CLUSTER_NAME} \
  --approve

# Download IAM policy
curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.0/docs/install/iam_policy.json

# Create IAM policy
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam_policy.json || true

# Create service account
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install load balancer controller using Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=${CLUSTER_NAME} \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

echo "✅ EKS cluster setup complete!"
echo "📝 Update kubeconfig: aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}"
