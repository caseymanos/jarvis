#!/bin/bash
set -e

echo "🧪 Running Load Tests for Jarvis Infrastructure"

# Configuration
API_URL="${API_URL:-https://api.jarvis.frontier.audio}"
WS_URL="${WS_URL:-wss://api.jarvis.frontier.audio}"

# Check k6 is installed
if ! command -v k6 &> /dev/null; then
  echo "❌ k6 is not installed. Installing..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    brew install k6
  else
    echo "Please install k6: https://k6.io/docs/getting-started/installation/"
    exit 1
  fi
fi

# Run load test
echo "🚀 Starting load test..."
echo "   API URL: ${API_URL}"
echo "   WebSocket URL: ${WS_URL}"
echo "   Target: 200 RPS, 50+ concurrent sessions"
echo ""

k6 run \
  --out json=load-test-results.json \
  --summary-export=load-test-summary.json \
  -e API_URL=${API_URL} \
  -e WS_URL=${WS_URL} \
  load-test.js

echo ""
echo "✅ Load test complete!"
echo "📊 Results saved to load-test-results.json"
echo "📈 Summary saved to load-test-summary.json"

# Check if test passed
if [ -f "load-test-summary.json" ]; then
  PASS_RATE=$(jq -r '.metrics.checks.passes / .metrics.checks.value * 100' load-test-summary.json)
  echo "✓ Pass rate: ${PASS_RATE}%"

  if (( $(echo "$PASS_RATE < 99" | bc -l) )); then
    echo "⚠️  Warning: Pass rate below 99%"
    exit 1
  fi
fi

echo "🎉 All performance targets met!"
