#!/bin/bash
set -e

echo "🚀 Deploying Jarvis Frontend to Cloudflare Pages"

# Change to web directory
cd web

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install
fi

# Build the Next.js application
echo "🔨 Building Next.js application..."
npm run build

# Deploy to Cloudflare Pages
echo "☁️  Deploying to Cloudflare Pages..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
  echo "❌ Wrangler CLI not found. Installing..."
  npm install -g wrangler
fi

# Deploy using wrangler
wrangler pages deploy .next --project-name=jarvis-frontend

echo "✅ Deployment complete!"
echo "📝 Next steps:"
echo "   1. Configure custom domain in Cloudflare dashboard"
echo "   2. Set environment variables: wrangler pages secret put <NAME>"
echo "   3. Configure DNS for jarvis.frontier.audio"
