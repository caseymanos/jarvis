#!/bin/bash
set -e

echo "🚀 Deploying Jarvis Backend to AWS ECS Fargate"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-2}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
CLUSTER_NAME="${CLUSTER_NAME:-jarvis-cluster}"
SERVICE_NAME="${SERVICE_NAME:-jarvis-backend}"
TASK_FAMILY="${TASK_FAMILY:-jarvis-backend-task}"
ECR_REPO="${ECR_REPO:-jarvis-backend}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "📋 Configuration:"
echo "  Region: $AWS_REGION"
echo "  Account: $AWS_ACCOUNT_ID"
echo "  Cluster: $CLUSTER_NAME"

# Step 1: Create ECR repository if it doesn't exist
echo ""
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION 2>/dev/null || \
  aws ecr create-repository \
    --repository-name $ECR_REPO \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true

# Step 2: Build and push Docker image
echo ""
echo "🐳 Building Docker image..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../backend"
docker build -t $ECR_REPO:$IMAGE_TAG .

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "📤 Pushing image to ECR..."
docker tag $ECR_REPO:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

# Step 3: Create ECS cluster if it doesn't exist
echo ""
echo "🏗️  Creating ECS cluster..."
aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null | grep -q ACTIVE || \
  aws ecs create-cluster \
    --cluster-name $CLUSTER_NAME \
    --region $AWS_REGION \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1

# Step 4: Create task execution role if it doesn't exist
echo ""
echo "🔑 Creating IAM role for task execution..."
ROLE_ARN=$(aws iam get-role --role-name ecsTaskExecutionRole --query 'Role.Arn' --output text 2>/dev/null || echo "")
if [ -z "$ROLE_ARN" ]; then
  aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'

  aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

  ROLE_ARN="arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole"
fi

# Step 5: Register task definition
echo ""
echo "📝 Registering task definition..."
cat > task-definition.json <<EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "$ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "jarvis-backend",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "PORT", "value": "8000"},
        {"name": "ENV", "value": "production"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$TASK_FAMILY",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region $AWS_REGION

rm task-definition.json

# Step 6: Get default VPC and subnets
echo ""
echo "🌐 Getting VPC configuration..."
DEFAULT_VPC=$(aws ec2 describe-vpcs --region $AWS_REGION --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$DEFAULT_VPC" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')

# Create security group
echo ""
echo "🔒 Creating security group..."
SG_ID=$(aws ec2 describe-security-groups --region $AWS_REGION --filters "Name=group-name,Values=jarvis-backend-sg" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
if [ "$SG_ID" == "None" ] || [ -z "$SG_ID" ]; then
  SG_ID=$(aws ec2 create-security-group \
    --group-name jarvis-backend-sg \
    --description "Security group for Jarvis backend" \
    --vpc-id $DEFAULT_VPC \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text)

  aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION
fi

# Step 7: Create or update service
echo ""
echo "🚀 Creating ECS service..."
aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null | grep -q ACTIVE && {
  echo "Service exists, updating..."
  aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --desired-count 2 \
    --region $AWS_REGION \
    --force-new-deployment
} || {
  echo "Creating new service..."
  aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_FAMILY \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region $AWS_REGION
}

echo ""
echo "✅ Deployment complete!"
echo "📊 Check status: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
echo "📝 View logs: aws logs tail /ecs/$TASK_FAMILY --follow --region $AWS_REGION"
