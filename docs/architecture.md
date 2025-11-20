# Jarvis - System Architecture

## Architecture Overview

This document describes the system architecture for Jarvis, a real-time voice assistant that merges always-on voice capture, hybrid Retrieval-Augmented Generation (RAG), and supervisor collaboration. The architecture follows a hub-and-spoke pattern: lightweight edge clients capture and pre-filter data, while a FastAPI + Temporal core orchestrates retrieval, grounding, and synthesis with strict guardrails for zero hallucinations.

---

## Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        subgraph "Next.js Voice Console"
            UI[UI Components]
            subgraph "Components Layer"
                VoiceHUD[Voice HUD\nWaveform/Latency\nStart/Interrupt]
                MissionBoard[Mission Board\nTranscripts/Notes]
                SupervisorTools[Supervisor Tools\nAnnotations/Pointers]
                Layout[Layout Shell\nNavbar/Footer]
            end
            subgraph "State Management"
                VoiceCtx[Voice Context\n(session tokens, VAD state)]
                MissionCtx[Mission Context\n(transcripts, notes, locks)]
            end
            subgraph "Custom Hooks"
                useAudio[useAudioStream\nStart/stop, metering]
                useMission[useMissionData\nsubscribe, mutate]
                usePresence[usePresence\nreal-time pointers]
                useLatency[useLatency\nSSE metrics]
            end
            subgraph "Services Layer"
                AuthService[Auth Service\nNextAuth + Azure AD]
                MissionService[Mission Service\nCRUD + locks]
                RetrievalService[Retrieval Service\nquery orchestrator]
                PresenceService[Presence Service\nWebSocket events]
                BackendInit[Backend Client Init\nEnv config]
            end
            subgraph "Rendering Engine"
                CanvasRenderer[Konva/Canvas\n60 FPS target]
            end
            subgraph "Utilities"
                Helpers[Helper Functions\nformatters, hashing]
                Constants[Constants\npalette, limits]
            end
        end
        subgraph "Android/iOS Edge"
            EdgeFGS[Foreground Service\nAudioRecord + Porcupine]
            EdgeCache[sqlite-vec Cache\nCouchbase Lite mirror]
        end
    end

    subgraph "Backend Services"
        AuthAPI[Auth (Azure AD + NextAuth)]
        subgraph "Temporal Cluster"
            Temporal[Temporal Workflows\nvoice session orchestration]
        end
        FastAPI[FastAPI Orchestrator\nRAG, LLM guardrails]
        Postgres[(Neon Postgres + pgvector\nmissions, transcripts)]
        Couchbase[(Couchbase Server\nSync Gateway)]
        Redis[(Redis Streams/Upstash\npresence, pub/sub)]
        ObjectStore[(S3 + Lance format\ndocuments)]
        LLMRouter[LLM Router\nGemini/Claude/local GGUF]
    end

    subgraph "Testing Infrastructure"
        Vitest[Vitest + React Testing Library]
        Pytest[Pytest + Httpx]
        TemporalTest[Temporal Test Server]
        Localstack[Localstack/Redis Test Containers]
    end

    VoiceHUD --> VoiceCtx
    MissionBoard --> MissionCtx
    SupervisorTools --> MissionCtx
    Layout --> VoiceCtx

    VoiceCtx --> useAudio
    MissionCtx --> useMission
    MissionCtx --> usePresence
    VoiceCtx --> useLatency

    useAudio --> RetrievalService
    useMission --> MissionService
    usePresence --> PresenceService
    useLatency --> MissionService

    RetrievalService --> BackendInit
    MissionService --> BackendInit
    PresenceService --> BackendInit
    AuthService --> BackendInit

    BackendInit --> AuthAPI
    BackendInit --> FastAPI
    BackendInit --> Redis

    EdgeFGS --> EdgeCache
    EdgeCache --> Couchbase
    EdgeFGS --> FastAPI

    FastAPI --> Temporal
    Temporal --> FastAPI
    FastAPI --> Postgres
    FastAPI --> Redis
    FastAPI --> LLMRouter
    FastAPI --> ObjectStore

    Couchbase --> FastAPI
    Postgres --> MissionService
    Redis --> PresenceService

    UI -.->|Build & Deploy\n`npm run deploy`| Hosting[Cloudflare Pages]
    Hosting --> Users
    Users --> UI

    Vitest -.-> MissionService
    Vitest -.-> Helpers
    Pytest -.-> FastAPI
    TemporalTest -.-> Temporal
    Localstack -.-> Redis
```

---

## System Components

### Frontend Architecture

#### 1. Components Layer

**Voice HUD Components**
- **Purpose**: Capture, visualize, and control live audio sessions.
- **Key Components**:
  - `WaveformCanvas.tsx`: renders waveform + clipping indicators.
  - `LatencyGauge.tsx`: shows backend RTT + color-coded status.
  - `TransportControls.tsx`: start/stop/interrupt buttons with hotkeys.
- **Specifications**: Uses Canvas + requestAnimationFrame for 60 FPS; stops rendering when tab hidden.

**Mission Board Components**
- **Purpose**: Display transcripts, grounding citations, and mission notes.
- **Key Components**:
  - `TranscriptList.tsx`: virtualized list of transcript cards.
  - `SourceBadge.tsx`: links every answer to its doc + confidence score.
  - `MissionNotes.tsx`: collaborative note pad with lock indicators.
- **Specifications**: Each transcript chunk capped at 512 chars; virtualization keeps memory <50 MB.

**Supervisor Tools**
- **Purpose**: Provide oversight annotations and pointer overlays.
- **Key Components**:
  - `PointerLayer.tsx`: renders remote cursors with smoothing.
  - `AnnotationPanel.tsx`: structured comment feed with timestamps.
  - `AlertBanner.tsx`: surfaces “No grounded answer” events.

**Layout Components**
- **Purpose**: Global chrome shared between operator + supervisor modes.
- **Key Components**:
  - `AppShell.tsx`: header (logo, presence), main content, command palette slot.
  - `SideTray.tsx`: collapsible panel for mission selection + logs.

#### 2. State Management

**Voice Context**
- **State**: media permissions, active sessionId, VAD status, latency metrics, interrupt flag.
- **Methods**: `startSession`, `stopSession`, `sendInterrupt`, `setLatency`. 
- **Purpose**: Keep transport state consistent across HUD components.

**Mission Context**
- **State**: transcripts[], mission metadata, locks map, reranker thresholds.
- **Methods**: `appendTranscript`, `lockNotes`, `unlockNotes`, `applySupervisorAnnotation`.
- **Purpose**: Single source of truth for collaborative data in the browser.

#### 3. Custom Hooks

**useAudioStream**
- **Purpose**: Manage MediaRecorder/WebRTC, chunk encoding, and network back-pressure.
- **Returns**: `start()`, `stop()`, `onChunk(cb)`, `isMuted`, `level`.
- **Operations**: toggles VAD gate, feeds PCM frames to backend via WebSocket.

**useMissionData**
- **Purpose**: Subscribe to Transcript SSE + mutate mission notes.
- **Returns**: `transcripts`, `notes`, `mutateNote`, `deleteChunk`.
- **Operations**: handles optimistic updates + conflict toasts.

**usePresence**
- **Purpose**: Subscribe to Redis/Ably channel for pointers + status.
- **Returns**: `pointers`, `onlineUsers`.
- **Operations**: throttle pointer updates to 30 FPS; auto-remove stale clients.

**useLatency**
- **Purpose**: Measure RTT by pinging FastAPI every 5 s.
- **Returns**: `latencyMs`, `statusBadge`.
- **Operations**: updates Voice HUD gauge + triggers alerts when >400 ms.

#### 4. Services Layer

**Auth Service**
- **Responsibilities**: NextAuth adapter, Azure AD OIDC, session refresh.
- **Key Functions**: `signIn()`, `signOut()`, `getSession()`, `requireRole()`.

**Mission Service**
- **Responsibilities**: CRUD on missions/transcripts, lock management, SSE stream subscribe.
- **Key Functions**: `fetchMission()`, `appendTranscript()`, `lockNotes()`, `unlockNotes()`.

**Retrieval Service**
- **Responsibilities**: Initiate voice session, send control frames, handle streaming responses.
- **Key Functions**: `startVoiceSession()`, `sendChunk()`, `interruptSession()`, `subscribeTranscript()`.

**Presence Service**
- **Responsibilities**: Publish pointer positions + listen to presence updates.
- **Key Functions**: `setOnline()`, `updatePointer()`, `removePointer()`.

#### 5. Rendering Engine

**Konva/Canvas Layer**
- **Purpose**: Render waveforms, pointers, and annotation overlays with 60 FPS target.
- **Key Features**: GPU-accelerated transforms, pooling for pointer sprites, fallback to DOM when Canvas unsupported.

#### 6. Utilities

**Helper Functions**
- `formatLatency(ms)`: bucketization for gauges.
- `hashToColor(userId)`: deterministic palette selection.
- `throttlePointer(fn)`: ensures ≤30 updates/sec per user.

**Constants**
- `LATENCY_THRESHOLDS = {good: 200, warn: 400, bad: 800}`
- `POINTER_COLORS = [...]`
- `MAX_TRANSCRIPT_CHARS = 512`

---

### Backend Architecture

#### 1. Authentication Service

**Provider**: Azure AD (OIDC) + NextAuth adapter. 
**Purpose**: Issue short-lived ID tokens for web + Android clients, map to Frontier Audio tenants.

```json
{
  "uid": "uid_1234",
  "email": "pilot@acme.com",
  "displayName": "Jordan Reyes",
  "tenantId": "acme",
  "roles": ["operator"],
  "callsign": "ACME-41"
}
```

#### 2. Primary Database (Persistent Storage)

**Database**: Neon Postgres with pgvector extension. 
**Purpose**: Store missions, transcripts, embeddings, notes, audit logs.

Operations: transactional inserts via FastAPI, logical replication to analytics warehouse, asynchronous embedding writes.

#### 3. Edge Database

**Database**: Couchbase Lite + sqlite-vec (on Android/iOS). 
**Purpose**: Cache hottest procedures for offline zero-hallucination guardrails; sync via Couchbase Sync Gateway into central Couchbase Server.

#### 4. Real-time Fabric

**Redis Streams / Upstash**
- **Purpose**: Low-latency fan-out for presence, agent states, pointer positions.
- **Features**: `XREAD` for ordered transcripts, TTL cleanup, `onDisconnect` semantics via server heartbeats.

#### 5. Workflow Orchestration

**Temporal Cloud**
- VoiceSessionWorkflow handles: VAD gating, Stage-2 speaker verification, Stage-3 retrieval, reranker, synthesis, and streaming back to clients.
- Activities talk to FastAPI microservices, LLM router, and storage.

#### 6. ML / LLM Layer

- **Embeddings**: `text-embedding-3-large` (cloud) + MiniLM (edge) with quantization for sqlite-vec.
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-12-v2` distilled + quantized to int8 for device use.
- **LLM Router**: Sequencing Gemini 1.5 Pro, Claude 3.5 Sonnet, fallback to local GGUF via llama.cpp for resilience.

---

## Data Flow Patterns

### 1. Voice Query Flow

```
Edge/Browser Audio → useAudioStream → WebSocket → FastAPI Ingress → Temporal Workflow
  → Stage 1: VAD check (edge) → Stage 2: Speaker Verification → Stage 3: Retrieval (BM25 + sqlite-vec + pgvector)
  → Reranker threshold check → LLM synthesis (if grounded) → Streaming response → SSE/WebSocket to clients → UI render
```

Latency budget: 80 ms edge capture, 120 ms retrieval, 200 ms synthesis start, 100 ms render.

### 2. Document Ingestion Flow

```
Operator Upload CLI → S3 (Lance format) → Async ingestion job → Split into chunks → Compute embeddings (cloud + edge fingerprints)
→ Store metadata in Postgres & Couchbase → Push quantized vectors to sqlite-vec templates for devices → Update Sync Gateway channels.
```

### 3. Presence Flow

```
Client mount → setOnline() → Redis Stream entry + onDisconnect() hook
→ Other clients subscribed via WebSocket/Ably → update pointer + roster
→ Client unmount or disconnect → onDisconnect cleans entry → broadcasts removal.
```

### 4. Mission Note Lock Flow

```
User clicks note → MissionService requests lock → Temporal activity writes lock row in Postgres → Broadcast lock status to all clients
→ User edits note → save → unlock issued → lock cleared → queued edits replay.
```

---

## Performance Characteristics

| Metric | Target | Notes |
| --- | --- | --- |
| UI Frame Rate | 60 FPS | Waveform/pointers animations |
| Voice Latency | <500 ms P95 | Portal to backend via Global Accelerator |
| Transcript Fan-out | <250 ms | Redis pub/sub + SSE |
| Pointer Update | <120 ms | 30 FPS throttle |
| Lock Acquisition | <80 ms | Temporal + Postgres transaction |
| Offline Cache Sync | <5 s | Couchbase delta sync |

Optimization strategies: audio chunk batching (320 samples), HTTP/2 SSE for transcripts, CDN caching for static assets, edge quantization for sqlite-vec to stay in RAM, incremental doc sync.

---

## Security Architecture

- Azure AD enforces MFA + conditional access.
- FastAPI validates JWTs, maps to tenant via claims.
- Postgres Row Level Security ensures tenant isolation.
- Redis namespaces per tenant to avoid pointer leaks.
- All vector stores store encrypted blobs at rest; TLS 1.3 for all transport.
- Audit logging via Temporal + CloudWatch for every transcript chunk.

---

## Testing Strategy

- **Frontend**: Vitest + React Testing Library for components/hooks; Playwright for WebRTC happy path.
- **Backend**: Pytest for FastAPI routes, Temporal test server for workflow determinism, contract tests for Redis + Couchbase interactions.
- **Edge**: Espresso tests for Android FGS, synthetic audio to validate VAD gating.

---

## Deployment Architecture

- Next.js deployed to Cloudflare Pages (preview + production channels).
- Backend packaged as containers, deployed to AWS EKS Fargate via GitHub Actions.
- Temporal Cloud handles workflow; Redis (Upstash) serverless for presence.
- Global Accelerator fronts FastAPI for consistent latency.
- Android APK distributed via Intune/MDM; config via remote feature flags (ConfigCat).

---

## Scalability Considerations

- Horizontal pod autoscaling based on active voice sessions + CPU.
- Shard Couchbase/pgvector per tenant once >50 missions/day.
- Future multi-region: replicate Postgres via read replicas; stride ingestion into S3 + Snowflake for analytics.
- LLM router supports new providers via config.

---

## Monitoring & Observability

- Datadog for FastAPI metrics (latency, errors, throughput).
- Temporal visibility UI for workflow tracing.
- Redis/Ably metrics for connection counts.
- Browser RUM (Sentry) for latency + JS errors.
- Alerts: latency >400 ms, transcript failure rate >1%, lock queue >5 pending.

---

## Technology Choices Rationale

- **Next.js + React**: fastest path for SSR + streaming UI; team familiarity.
- **FastAPI + Temporal**: Python ecosystem for LLM tooling + deterministic workflow + interruption control.
- **Couchbase Lite + sqlite-vec**: proven offline-first vector cache; matches aviation-style zero hallucination requirement.
- **Neon Postgres + pgvector**: SQL + vector operations + logical replication.
- **Redis/Upstash**: serverless pub/sub with predictable latency.

---

## Known Issues & Technical Debt

1. Need automated doc ingestion UI (CLI only).
2. Supervisor console not yet optimized for tablets.
3. Edge cache invalidation manual; requires OTA update process.
4. No dedicated blue/green deploy pipeline yet.
5. Temporal single namespace; should split staging/production later.

---

## References

- FastAPI docs
- Temporal.io docs
- Couchbase Lite vector search guide
- sqlite-vec documentation
- Project PRD: `docs/PRD.md`
- Task List: `docs/tasks.md`
```
