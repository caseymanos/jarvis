#!/bin/bash
set -e

echo "🌐 Setting up AWS Global Accelerator for low-latency ingress"

# Configuration
ACCELERATOR_NAME="jarvis-global-accelerator"
AWS_REGION="${AWS_REGION:-us-west-2}"

# Create Global Accelerator
echo "🚀 Creating Global Accelerator..."
ACCELERATOR_ARN=$(aws globalaccelerator create-accelerator \
  --name ${ACCELERATOR_NAME} \
  --ip-address-type IPV4 \
  --enabled \
  --query 'Accelerator.AcceleratorArn' \
  --output text)

echo "📝 Accelerator ARN: ${ACCELERATOR_ARN}"

# Wait for accelerator to be deployed
echo "⏳ Waiting for accelerator to deploy..."
aws globalaccelerator wait accelerator-deployed --accelerator-arn ${ACCELERATOR_ARN}

# Get static IPs
STATIC_IPS=$(aws globalaccelerator describe-accelerator \
  --accelerator-arn ${ACCELERATOR_ARN} \
  --query 'Accelerator.IpSets[0].IpAddresses' \
  --output text)

echo "📍 Static IPs: ${STATIC_IPS}"

# Create listener for HTTP/HTTPS traffic
echo "👂 Creating listener..."
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --accelerator-arn ${ACCELERATOR_ARN} \
  --port-ranges FromPort=80,ToPort=80 FromPort=443,ToPort=443 \
  --protocol TCP \
  --query 'Listener.ListenerArn' \
  --output text)

echo "📝 Listener ARN: ${LISTENER_ARN}"

# Get ALB ARN (from EKS ingress)
echo "⚠️  Manual step required:"
echo "   1. Deploy the backend to EKS to create the ALB"
echo "   2. Get the ALB ARN from AWS Console or CLI"
echo "   3. Create endpoint group with:"
echo ""
echo "   aws globalaccelerator create-endpoint-group \\"
echo "     --listener-arn ${LISTENER_ARN} \\"
echo "     --endpoint-group-region ${AWS_REGION} \\"
echo "     --endpoint-configurations EndpointId=<ALB_ARN>,Weight=100 \\"
echo "     --traffic-dial-percentage 100 \\"
echo "     --health-check-interval-seconds 30 \\"
echo "     --health-check-path /health"
echo ""
echo "   4. Update DNS to point to Global Accelerator IPs: ${STATIC_IPS}"

echo "✅ Global Accelerator setup initiated!"
echo "📝 Note: Complete manual steps above to finish configuration"
