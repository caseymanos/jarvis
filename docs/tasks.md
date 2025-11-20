# Jarvis MVP - Development Task List

## Project File Structure

```
jarvis/
├── apps/
│   ├── web/ (Next.js App Router)
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── (session)/[sessionId]/page.tsx
│   │   ├── components/
│   │   │   ├── VoiceHUD/
│   │   │   │   ├── WaveformCanvas.tsx
│   │   │   │   ├── LatencyGauge.tsx
│   │   │   │   └── TransportControls.tsx
│   │   │   ├── MissionBoard/
│   │   │   │   ├── TranscriptList.tsx
│   │   │   │   ├── SourceBadge.tsx
│   │   │   │   └── MissionNotes.tsx
│   │   │   ├── Collaboration/
│   │   │   │   ├── PointerLayer.tsx
│   │   │   │   ├── PresenceList.tsx
│   │   │   │   └── AnnotationPanel.tsx
│   │   │   └── Layout/
│   │   │       ├── AppShell.tsx
│   │   │       └── SideTray.tsx
│   │   ├── hooks/
│   │   │   ├── useAudioStream.ts
│   │   │   ├── useMissionData.ts
│   │   │   ├── usePresence.ts
│   │   │   └── useLatency.ts
│   │   ├── lib/
│   │   │   ├── auth.ts
│   │   │   ├── mission.ts
│   │   │   ├── retrieval.ts
│   │   │   └── presence.ts
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   │   ├── hooks/
│   │   │   │   │   └── useAudioStream.test.ts
│   │   │   │   └── components/
│   │   │   │       └── WaveformCanvas.test.tsx
│   │   │   └── integration/
│   │   │       └── voice-session.test.ts
│   │   └── package.json
│   └── backend/ (FastAPI + Temporal workers)
│       ├── app/
│       │   ├── main.py
│       │   ├── routers/
│       │   │   ├── auth.py
│       │   │   ├── missions.py
│       │   │   └── voice.py
│       │   ├── services/
│       │   │   ├── retrieval.py
│       │       ├── embeddings.py
│       │       └── reranker.py
│       │   ├── workflows/
│       │   │   └── voice_session.py
│       │   ├── models/
│       │   │   └── mission.py
│       │   └── tests/
│       │       └── test_voice_session.py
│       ├── pyproject.toml
│       └── requirements.txt
├── android-edge/
│   ├── app/src/main/java/... (FGS + sqlite-vec cache)
│   └── build.gradle
├── infra/
│   ├── k8s/
│   ├── terraform/
│   └── temporal/
├── docs/
│   ├── PRD.md
│   ├── architecture.md
│   └── tasks.md
├── package.json (workspaces)
├── turbo.json (or nx.json)
├── .env
├── .env.example
└── README.md
```

---

## PR #1: Monorepo & Environment Bootstrap

**Branch:** `setup/monorepo-foundation`  
**Goal:** Initialize pnpm/Turbo monorepo with Next.js app, FastAPI backend scaffold, shared tooling, and env wiring.

### Tasks:

- [ ] **1.1: Initialize pnpm workspace + Turbo**
  - Files: root `package.json`, `pnpm-workspace.yaml`, `turbo.json`
  - Commands: `pnpm dlx create-next-app@latest apps/web --ts --app`, `python -m venv .venv && pip install fastapi uvicorn`
  - Verify `pnpm dev --filter web` + `uvicorn app.main:app --reload`

- [ ] **1.2: Configure shared lint/format**
  - Add ESLint + Prettier configs, Ruff for Python, EditorConfig

- [ ] **1.3: Set up FastAPI skeleton**
  - Create routers (`auth.py`, `voice.py`), placeholder endpoints (`/healthz`, `/sessions`)

- [ ] **1.4: Environment files**
  - Create `.env`, `.env.example` with placeholders for Azure AD, Postgres, Redis, Temporal, Couchbase
  - Ensure `.env` ignored via `.gitignore`

- [ ] **1.5: README baseline**
  - Outline repo layout, dev commands, env vars, how frontend + backend run locally

**PR Checklist:**

- [ ] `pnpm dev --filter web` renders default page
- [ ] `uvicorn app.main:app --reload` responds `200 /healthz`
- [ ] Lint/format scripts succeed for both stacks
- [ ] `.env` excluded from git

---

## PR #2: Authentication & Session Guardrails

**Branch:** `feature/auth-session`

### Tasks:

- [ ] **2.1 NextAuth setup**
  - Files: `apps/web/app/api/auth/[...nextauth]/route.ts`
  - Providers: Email/password (Credentials) + Azure AD (OIDC)
  - Persist sessions with Prisma (SQLite dev) or pg

- [ ] **2.2 Auth UI**
  - Components: `LoginForm`, `SSOButton`, `LogoutButton`
  - Display name logic & truncation implemented globally

- [ ] **2.3 Backend token validation**
  - FastAPI dependency to verify NextAuth/JWT tokens, map to tenant/roles

- [ ] **2.4 Protected routes**
  - Guard `/session/[sessionId]` and backend `/missions/*`

- [ ] **2.5 Tests**
  - Vitest for login form validation
  - Pytest for auth dependency (mock JWKS)

**Checklist:**

- [ ] Can sign up/in/out
- [ ] Azure AD login works against dev tenant
- [ ] Protected routes redirect unauth users
- [ ] Display names stable across reloads

---

## PR #3: Voice HUD & Audio Transport (Frontend)

**Branch:** `feature/voice-hud`

### Tasks:

- [ ] **3.1 Media permissions + wake word placeholder**
  - Hook `useAudioStream` with MediaRecorder + Porcupine stub

- [ ] **3.2 WebSocket/WebRTC transport layer**
  - Connect to backend `/ws/voice`
  - Implement exponential backoff + heartbeat pings

- [ ] **3.3 Waveform + latency components**
  - Canvas-based waveform, indicator colors per latency bucket

- [ ] **3.4 Interrupt control**
  - Map button + `space` hotkey to send `INTERRUPT`

- [ ] **3.5 Tests**
  - Simulate audio chunk flow w/ mocked WS
  - Snapshot waveform + latency gauge states

**Checklist:**

- [ ] Start/stop voice capture works
- [ ] Interrupt stops streaming instantly
- [ ] Latency gauge updates every 5 s
- [ ] Handles network drops gracefully

---

## PR #4: Backend Voice Pipeline (FastAPI + Temporal)

**Branch:** `feature/voice-backend`

### Tasks:

- [ ] **4.1 Temporal VoiceSessionWorkflow**
  - Activities: `start_stream`, `call_sv`, `hybrid_retrieval`, `synthesize`

- [ ] **4.2 WebSocket ingress**
  - Endpoint `/ws/voice` ingesting PCM frames, publishing to workflow queue

- [ ] **4.3 Speaker verification gate**
  - Integrate `webrtcvad` + `azure speaker verification` or `Resemblyzer`

- [ ] **4.4 Hybrid retrieval stub**
  - BM25 via Tantivy, pgvector for dense, sqlite-vec parity check

- [ ] **4.5 Streaming responses**
  - SSE endpoint `/sessions/{id}/stream` broadcasting transcript tokens

- [ ] **4.6 Tests**
  - Temporal worker unit tests
  - Pytest for WebSocket flows (starlette test client)

**Checklist:**

- [ ] VAD/SV gating functional
- [ ] Retrieval stage returns citations
- [ ] SSE emits tokens to mocked client
- [ ] Workflow cancellation (interrupt) works

---

## PR #5: Knowledge Store & Edge Sync

**Branch:** `feature/rag-grounding`

### Tasks:

- [ ] **5.1 Postgres schema (missions, transcripts, embeddings)**
- [ ] **5.2 Couchbase Server + Sync Gateway config**
  - Channels per tenant, delta sync enabled

- [ ] **5.3 sqlite-vec packaging for Android/iOS**
  - Script to export quantized vectors from Postgres to edge bundle

- [ ] **5.4 Hybrid fusion service**
  - Implement RRF combination (BM25 rank + cosine distance)
  - Apply reranker threshold 0.88

- [ ] **5.5 Document ingestion CLI**
  - Upload PDF/Markdown to S3 → chunk → embed → store metadata

- [ ] **5.6 Tests**
  - Golden dataset to confirm zero hallucination (no unmatched doc)
  - Couchbase sync integration test (sync once, offline mode)

**Checklist:**

- [ ] Documents ingest end-to-end
- [ ] Edge cache populated + validated offline
- [ ] Retrieval returns citations + fails closed when no match

---

## PR #6: Mission Board & Collaboration UI

**Branch:** `feature/mission-board`

### Tasks:

- [ ] **6.1 TranscriptList (virtualized)**
- [ ] **6.2 MissionNotes editor with lock indicator**
- [ ] **6.3 SourceBadge + confidence chips**
- [ ] **6.4 AnnotationPanel for supervisors**
- [ ] **6.5 Tests**: React Testing Library for lock states + virtualization boundaries

**Checklist:**

- [ ] Transcript updates render without jank
- [ ] Notes lock/unlock visually clear
- [ ] Annotations broadcast to all viewers

---

## PR #7: Real-Time Presence & Pointer System

**Branch:** `feature/presence-pointers`

### Tasks:

- [ ] **7.1 Redis/Ably channel wiring**
  - `presence:{missionId}` stream with TTL

- [ ] **7.2 usePresence hook**
  - Subscribe, throttle, cleanup on unmount, onDisconnect

- [ ] **7.3 PointerLayer component**
  - Smooth transitions, collision avoidance near edges

- [ ] **7.4 PresenceList UI**
  - Show status pill (listening/thinking/degraded)

- [ ] **7.5 Tests**
  - Simulate two browsers, ensure cleanup occurs

**Checklist:**

- [ ] Unique colors per user
- [ ] Instant join/leave updates
- [ ] Pointer updates <120 ms

---

## PR #8: Transcript Management & Deletion Guardrails

**Branch:** `feature/transcript-controls`

### Tasks:

- [ ] **8.1 Delete API + ACL**
  - FastAPI endpoint verifying permissions + lock state

- [ ] **8.2 Frontend shortcuts**
  - `Shift+Backspace` + long-press context menu

- [ ] **8.3 Hard delete in Postgres + cache purge**
  - Ensure removed chunks excluded from future retrieval

- [ ] **8.4 Audit logging**
  - Temporal activity writes audit row (who/when/why)

- [ ] **8.5 Tests**
  - Pytest verifying GDPR erasure (no record remains)
  - Frontend E2E covering keyboard + mobile gestures

**Checklist:**

- [ ] Deletion propagates <250 ms
- [ ] Deleted chunk never reappears after refresh
- [ ] Audit log entry created

---

## PR #9: Performance, Testing, and Deployment

**Branch:** `release/mvp-hardening`

### Tasks:

- [ ] **9.1 Load + soak testing**
  - K6/Gatling scripts for 30 concurrent sessions
  - Measure <500 ms latency compliance

- [ ] **9.2 Offline + reconnection tests**
  - Android FGS kill/restart, browser refresh mid-session

- [ ] **9.3 Observability wiring**
  - Datadog APM, log correlation, Temporal alerts

- [ ] **9.4 CI/CD pipelines**
  - GitHub Actions: lint, test, build, deploy web (Cloudflare) + backend (EKS)

- [ ] **9.5 Security review**
  - Validate JWT scopes, Redis isolation, HTTPS everywhere

- [ ] **9.6 Documentation**
  - Update README (setup, scripts, known issues)
  - Record test evidence (video or gifs)

**Checklist:**

- [ ] All automated tests passing in CI
- [ ] Load tests meet SLA
- [ ] Production deploy accessible (SSO)
- [ ] Observability dashboards live

---

## MVP Completion Checklist

- [ ] Voice HUD with wake word, waveform, latency gauge
- [ ] Hybrid RAG with deterministic reranker + citations
- [ ] Android/iOS edge cache syncing via Couchbase Lite
- [ ] Real-time collaboration (notes, annotations, pointers)
- [ ] Presence + status indicators
- [ ] Transcript deletion meeting compliance rules
- [ ] Auth (email + Azure AD) + protected routes
- [ ] Production deployment + monitoring

---

## Post-MVP Roadmap Ideas

- PR #10: Multilingual ASR/TTS swap (Whisper + Bark)
- PR #11: Automated GitHub issue triage + PR drafting
- PR #12: Advanced analytics + timeline scrubber
- PR #13: Hardware integration (push-to-talk button)
- PR #14: Fine-grained RBAC + tenant admin portal
- PR #15: Multi-modal ingestion (imagery, schematics)
