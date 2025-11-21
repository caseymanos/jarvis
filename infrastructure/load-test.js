import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const websocketLatency = new Trend('websocket_duration');
const errorRate = new Rate('http_req_failed');

// Configuration
const BASE_URL = __ENV.API_URL || 'https://api.jarvis.frontier.audio';
const WS_URL = __ENV.WS_URL || 'wss://api.jarvis.frontier.audio';

export let options = {
  scenarios: {
    // Scenario 1: Sustained API load - 200 RPS
    api_load: {
      executor: 'constant-arrival-rate',
      rate: 200,
      timeUnit: '1s',
      duration: '5m',
      preAllocatedVUs: 100,
      maxVUs: 200,
      exec: 'apiLoadTest',
    },

    // Scenario 2: Concurrent voice sessions - 50+ sessions
    voice_sessions: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m',
      exec: 'voiceSessionTest',
    },
  },

  thresholds: {
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'http_req_failed': ['rate<0.01'],
    'websocket_duration': ['p(95)<200'],
  },
};

// API Load Test Function
export function apiLoadTest() {
  // Health check
  let healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check status 200': (r) => r.status === 200,
  });

  // Authentication
  const authPayload = JSON.stringify({
    email: `test-${__VU}@example.com`,
    password: 'testpassword123',
  });

  let authRes = http.post(`${BASE_URL}/api/auth/login`, authPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(authRes, {
    'auth successful': (r) => r.status === 200,
  });

  errorRate.add(authRes.status !== 200);

  // Query endpoint
  if (authRes.status === 200) {
    const token = authRes.json('token');

    let queryRes = http.get(`${BASE_URL}/api/query`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    check(queryRes, {
      'query successful': (r) => r.status === 200,
      'response time < 500ms': (r) => r.timings.duration < 500,
    });

    errorRate.add(queryRes.status !== 200);
  }

  sleep(1);
}

// Voice Session Test Function
export function voiceSessionTest() {
  const url = `${WS_URL}/ws/voice/${__VU}`;

  const res = ws.connect(url, {}, function (socket) {
    socket.on('open', () => {
      console.log(`VU ${__VU}: Connected to voice session`);

      // Simulate audio chunks
      for (let i = 0; i < 10; i++) {
        const startTime = Date.now();

        socket.send(JSON.stringify({
          type: 'audio_chunk',
          data: 'base64_encoded_audio_chunk',
          sequence: i,
        }));

        socket.on('message', (data) => {
          const latency = Date.now() - startTime;
          websocketLatency.add(latency);

          check(data, {
            'received response': (d) => d !== null,
          });
        });

        sleep(0.5); // Simulate realistic audio chunk intervals
      }
    });

    socket.on('error', (e) => {
      console.error(`VU ${__VU}: WebSocket error: ${e}`);
      errorRate.add(1);
    });

    socket.setTimeout(() => {
      socket.close();
    }, 10000);
  });

  check(res, {
    'WebSocket connection established': (r) => r && r.status === 101,
  });
}

export function handleSummary(data) {
  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}
