# Jarvis MVP - Product Requirements Document

**Project**: Jarvis - Real-time Voice Assistant for Frontline Operations  
**Goal**: Deliver a zero-hallucination, sub-500 ms voice-to-action loop that streams verified answers and task automations to frontline workers.

**Note**: Multilingual support, automated PR creation, and bespoke hardware accessories are intentionally deferred to Phase 2.

---

## Core Architecture (MVP)

**Edge-to-Cloud Hybrid Retrieval Stack:**

- MVP features a two-tier knowledge pipeline: the frontend (Next.js voice console + Android always-on client) captures audio, streams it to a FastAPI orchestration layer, and executes a deterministic hybrid RAG flow (BM25 + sqlite-vec edge index + Couchbase Lite sync + pgvector in Postgres) before any LLM synthesis.
- Not included: multi-region replication, per-aircraft document partitions, advanced AI assistant insights, or automated GitHub PR authoring.
- Single shared resource approach: one shared “Jarvis Core” workflow cluster (Temporal + Redis) fans answers out to all channels to keep latency predictable.
- Future: dedicated tenant shards, multimodal (image/video) embeddings, LanceDB cold storage tiers, and FAA/DO-178C certification tracks.

**URL Structure:**

- `jarvis.frontier.audio/` → Next.js app router entry point (SSR + streaming responses)
- `/session/[sessionId]` → active voice session UI (dynamic route; WebRTC + WebSocket transport)
- `/console/logs` → supervisor console (static shell with client-side data fetches)
- `/api/*` → FastAPI gateway exposed via API Gateway (REST + WebSocket upgrades)

---

## User Stories

### Primary User: Frontline Operator (MVP Priority)

- As a frontline operator, I want hands-free wake-word capture so that I can query Jarvis without slowing my work.
- As a frontline operator, I want answers grounded in my fleet’s SOPs so that I can trust every recommendation.
- As a frontline operator, I want GPS/time-stamped transcripts so that I have an auditable record of decisions.
- As a frontline operator, I want to interrupt Jarvis mid-response so that urgent corrections land immediately.
- As a frontline operator, I want offline fallbacks with cached procedures so that I can keep working when connectivity drops.

**Note:** Focus on completing all Frontline Operator stories before addressing Supervisor needs.

### Secondary User: Supervisor / Team Lead (Implement After Primary User)

- As a supervisor, I want live session visibility so that I can coach teams in real time.
- As a supervisor, I want alerting when Jarvis cannot find a grounded answer so that I can escalate to SMEs quickly.

---

## Key Features for MVP

### 1. Authentication System

**Must Have:**

- User registration via email/password
- Azure AD (OIDC) social login (company-issued accounts)
- User login/logout
- Persistent user sessions (NextAuth + HttpOnly cookies)
- User display names visible to team members and supervisors

**Display Name Logic:**

- Prefers Azure `displayName`; falls back to first + last from signup
- If both missing, use `callsign-XXXX` (last 4 of UID)
- Truncate UI rendering to 24 chars with ellipsis

**Success Criteria:**

- Users can create accounts and maintain sessions across refreshes
- Each user has a unique identifier and deterministic display name

### 2. Real-Time Voice Session Pipeline

**Must Have:**

- WebRTC/MediaRecorder capture at 16 kHz mono PCM
- Back-pressure aware WebSocket streaming to FastAPI ingress
- Round-trip <500 ms for VAD → SV → retrieval trigger
- Drop packets gracefully when bandwidth <50 kbps
- Visual waveform & latency indicator in UI

**Specific Behavior:**

- Wake-word gate (Porcupine) arms recording; silence >2 s auto-closes stream
- Edge sqlite-vec cache hit returns snippet instantly; cache miss escalates to cloud retrieval
- Interrupt button sends `INTERRUPT` control frame to backend, which aborts synthesis
- Fallback TTS uses cached responses if network unreachable for >5 s

**Success Criteria:**

- Voice capture feels responsive and smooth
- No audible/visible lag during query bursts
- Handles 30+ simultaneous segments without buffer overruns
- Guarantees single active synthesis per user session

### 3. Knowledge Retrieval & Task Routing

**Must Have:**

- **MVP limitation:** Text + structured data only (no images/video)
- Ability to ingest SOP PDFs, telemetry JSON, and GitHub markdown
- Ability to select retrieval scope (global, aircraft type, mission)
- Ability to rerank snippets via on-device cross-encoder (int8 quantized)
- Visual feedback for grounding sources + confidence badges

**Specific Behavior:**

- Hybrid query = BM25 (tantivy) + cosine similarity (sqlite-vec/pgvector) fused via RRF
- Snippet rejected if reranker score <0.88 (returns “No grounded answer”)
- Multi-select disabled for MVP; scope filter is single-select drop-down

**Success Criteria:**

- Retrieval actions are deterministic and immediate
- No hallucinated steps make it past reranker threshold
- Grounding metadata is always linked next to each answer
- Operators understand when/why fallback responses trigger

### 4. Real-Time Synchronization

**Must Have:**

- Broadcast transcript updates to all clients (<250 ms)
- Broadcast agent state (listening/thinking/speaking) (<150 ms)
- Broadcast supervisor annotations (<400 ms)
- Handle concurrent edits to mission notes without conflicts
- Optimistic locking on mission notes (Temporal activity lock)
- Presence indicator showing backend health + latency bucket
- Auto-release locks if owner disconnects or idle >30 s

**Conflict Resolution Strategy:**

- First writer wins; others receive toast with “view-only” warning
- When lock released, queued edits re-try automatically
- Locks auto-release after 30 s or upon successful commit
- UI surfaces lock owner + remaining hold time

**Success Criteria:**

- Transcript/agent state visible to everyone within targets
- No duplicate or missing log lines
- Mission notes never diverge between clients
- Lock visuals are obvious and self-resolving

### 5. Collaborative Session Indicators

**Must Have:**

- Show real-time cursor/pointer for each connected supervisor
- Display user call sign + role badge near pointer
- Update pointer positions in <120 ms
- Unique color per user derived from palette of 16 options

**Pointer Attributes:**

- Palette tuned for WCAG AA contrast on dark canvas
- Color persists across reconnects (hash of userId)
- Z-index never obscures transcript text

**Success Criteria:**

- Pointers move smoothly without jitter
- Labels readable yet unobtrusive
- Pointer updates have zero impact on audio loop
- No two users share the same color within a session

### 6. Transcript & Memory Deletion

**Must Have:**

- Delete transcript chunk with `Shift + Backspace` (desktop) or long-press menu (mobile)
- Broadcast deletions instantly
- Hard-delete from Postgres within 1 s (GDPR compliance)
- Cannot delete locked mission notes or regulatory mandates

**Success Criteria:**

- Deletion propagates <250 ms
- No ghost entries after refresh
- Deleted data absent from subsequent retrieval contexts

### 7. Presence Awareness

**Must Have:**

- List of online operators + supervisors per session
- Real-time join/leave toasts
- Status pill (online, muted, degraded network)

**Success Criteria:**

- Presence list accurate at all times
- Join/leave events broadcast instantly
- Status pill reflects audio capture health

### 8. State Persistence

**Must Have:**

- Persist mission sessions to Postgres (Durable Objects mirror for low-latency reads)
- Load last known state on reconnect
- Survive browser refresh or Android service restart
- Allow multiple devices per user to rejoin same session

**Success Criteria:**

- Full state restored after refresh/disconnect
- Offline work queue replays when back online
- New device sees complete context immediately

### 9. Deployment

**Must Have:**

- Public URL (Cloudflare Pages for web, custom domain)
- Backend deployed on AWS (EKS Fargate) with autoscaling to 200 RPS
- No install/setup required for supervisors; Android APK delivered via MDM

**Success Criteria:**

- Anyone with credentials can access URL
- Supports 50+ concurrent sessions
- No crashes under expected field load

---

## Data Model

### Postgres (pgvector) Table: `missions`

**Row ID:** `mission_${tenantId}_${date}`

```json
{
  "missionId": "mission_acme_2024-11-15",
  "tenantId": "acme-air",
  "aircraftType": "A320",
  "crew": [
    {"userId": "uid_1234", "role": "operator", "displayName": "J. Reyes"}
  ],
  "transcripts": [
    {
      "id": "chunk_01",
      "startsAt": "2024-11-15T08:21:14Z",
      "endsAt": "2024-11-15T08:21:30Z",
      "text": "Hydraulic pump A pressure stable...",
      "gps": {"lat": 47.4502, "lng": -122.3088},
      "sourceDocs": ["doc_fcq_2024-10"],
      "rerankerScore": 0.94,
      "isLocked": false,
      "lockedBy": null
    }
  ],
  "notes": "text",
  "lastUpdated": "timestamp"
}
```

### Redis/Upstash Realtime Channel: `/presence/{missionId}`

```json
{
  "mission_acme_2024-11-15": {
    "uid_1234": {
      "displayName": "J. Reyes",
      "color": "#F97316",
      "x": 420,
      "y": 180,
      "lastSeen": 1731684072000,
      "status": "listening"
    },
    "uid_5678": {
      "displayName": "Ops Chief",
      "color": "#14B8A6",
      "x": 120,
      "y": 360,
      "lastSeen": 1731684071000,
      "status": "monitoring"
    }
  }
}
```

**Why Two Databases?**

- **Postgres (pgvector + SQLite edge replicas):** For authoritative mission state, documents, and regulated audit trails.
- **Redis/Upstash Channels (or Ably):** For <150 ms presence, pointer, and agent-state updates; supports `onDisconnect` cleanup and throttled fan-out.

---

## Proposed Tech Stack

### Option 1: Edge-to-Cloud Hybrid (Recommended for zero-hallucination RAG)

**Frontend:**

- Next.js 15 (App Router) + React 19 streaming
- Radix UI + Tailwind for accessible components
- WebRTC + Web Audio for capture & playback
- Zustand for UI-only state, React Query for data

**Backend:**

- FastAPI + Uvicorn workers (Python) for LLM orchestration
- Temporal Cloud for workflow + interruption control
- Neon Postgres + pgvector for authoritative embeddings
- Couchbase Lite on Android/iOS + Sync Gateway for offline edge mirrors
- sqlite-vec on-device cache (int8 quantized) for hottest procedures
- Redis Streams for presence + event fan-out
- Gemini 1.5/Claude 3 Sonnet as guarded LLMs with strict grounding contract

**Pros:**

- Hybrid retrieval (lexical + vector) baked into Couchbase/sqlite-vec stack → minimal hallucinations
- Temporal handles cancellation & retries → deterministic latency
- Edge cache gives sub-150 ms answers even offline
- Already aligns with Android always-on architecture built earlier
- Easy to link Next.js frontend with FastAPI backend via WebSockets + SSE

**Cons:**

- Operational overhead (Temporal + Couchbase) vs fully managed SaaS
- Requires dual schema management (edge + cloud)
- Couchbase Lite licensing for enterprise grade features

**Pitfalls to Watch:**

- Sync Gateway conflicts if document sizes exceed 20 MB → chunk manuals
- Need deterministic hashing between sqlite-vec + pgvector to avoid embedding drift
- Temporal activities must be idempotent to survive retries (especially when cancelling speech)

---

### Option 2: Supabase + Qdrant Cloud Stack

**Frontend:**

- Next.js + shadcn/ui + TanStack Query

**Backend:**

- Supabase Auth/Postgres (pgvector) for persistence
- Edge Functions for lightweight routing
- Qdrant Cloud for vector search + payload filtering
- Ably or Pusher for real-time presence

**Pros:**

- Managed services reduce ops burden
- pgvector + Qdrant hybrid search available out of the box
- Supabase Row Level Security for tenant isolation

**Cons:**

- Offline story weaker (no embedded db)
- Qdrant Cloud introduces extra network hop (latency risk for 500 ms goal)
- Re-ranker + worker orchestration must be hand-rolled

**Pitfalls to Watch:**

- Supabase rate limits per project; need connection pooling
- Vector payload updates expensive—batch writes and avoid per-token updates
- Ably connections count toward plan; clean up sockets aggressively

---

### Option 3: Rust Microservices + LanceDB (Custom Backend)

**Frontend:**

- SvelteKit or SolidStart for ultra-low bundle size
- Custom WebAssembly audio DSP

**Backend:**

- Axum (Rust) + tonic gRPC for streaming
- LanceDB for multi-modal vector store on NVMe
- Kafka + Materialize for telemetry ingest
- Custom auth (JWT) or Ory Kratos

**Pros:**

- Ultimate performance + control, LanceDB great for future multimodal needs
- Rust audio processing can share code with embedded clients
- No vendor lock-in

**Cons:**

- Longest build time; requires deep Rust expertise
- LanceDB Swift bindings immature (harder for mobile cache)
- Must build auth + workflow semantics from scratch

**Pitfalls to Watch:**

- Need to manage gRPC load balancing + sticky sessions
- LanceDB compaction jobs can spike IO; schedule carefully
- Harder to hire for Rust + Lance combo

---

## Recommended Stack for MVP

**Frontend:** Next.js 15 + React 19 + Radix UI + Tailwind CSS  
**Backend:** Option 1 Hybrid Stack (FastAPI + Temporal + Couchbase Lite/sqlite-vec edge + Neon Postgres/pgvector + Redis Streams)  
**Deployment:** Cloudflare Pages (web) + AWS EKS Fargate (backend) + AWS Global Accelerator for low-latency ingress

**Rationale:** This stack reuses the existing Android always-on groundwork, hits the “speed + zero hallucination” mandate via deterministic hybrid retrieval, and keeps frontend/backend responsibilities clean so your teammate can ship UI independently.

---

## Out of Scope for MVP

### Features NOT Included:

- Advanced analytics dashboards (heatmaps, ops KPIs)
- Automated GitHub issue triage or PR generation
- Multilingual transcription/translation
- Hardware accessories beyond Bluetooth headsets
- Computer-vision ingestion (schematics, video)
- Deep AI agent chaining or autonomous task execution
- Custom tenant theming
- Field-level permissions or RBAC
- Batch document labeling workflows

### Technical Items NOT Included:

- Federated vector store across regions (single region only)
- Offline supervisor console
- Full observability stack (basic logging only)
- Historical versioning / timeline scrubber
- Model fine-tuning pipelines
- Advanced caching (CloudFront edge compute) beyond basic CDN

---

## Known Limitations & Trade-offs

1. **Single-region deployment:** All compute lives in us-west-2 (future multi-region failover).
2. **Edge cache size cap:** sqlite-vec cache limited to ~1 GB per device (rotate hottest docs daily).
3. **LLM dependency:** Gemini/Claude availability directly impacts response SLA (evaluate open models later).
4. **No multilingual:** English-only transcripts until ASR swap scheduled.
5. **Manual ingestion:** Docs ingested via CLI, no self-serve uploader yet.
6. **Supervisor UI web-only:** No native tablet experience until Phase 2.
7. **Temporal single cluster:** Workflow backlog could spike under mass reconnect events.
8. **Basic permissions:** Tenant-level isolation only; no per-document ACLs.

---

## Success Metrics for MVP Checkpoint

1. **<500 ms end-to-end latency** for 95th percentile voice queries.
2. **Refresh/reload resilience**: full session state restored after browser refresh or Android service restart.
3. **Rapid query bursts** (≥5 questions/min) sync without noticeable lag.
4. **Conflict resolution**: mission note locks behave deterministically with clear UX.
5. **RAG precision**: 0 hallucinated steps in golden test set (N=50) thanks to hybrid retrieval.
6. **Deployed + accessible** via production URL with SSO-protected login.

---

## MVP Testing Checklist

### Core Functionality:

- [ ] User can sign up (email/password)
- [ ] User can log in via Azure AD SSO
- [ ] Session persists after refresh
- [ ] Display name renders correctly in navbar + presence list

### Voice Pipeline Operations:

- [ ] Can start voice capture via wake word
- [ ] Can interrupt response and hear immediate stop
- [ ] Can resume conversation without reloading page
- [ ] Latency indicator stays <500 ms on wired network
- [ ] Audio packets drop gracefully under throttled network

### Retrieval Operations:

- [ ] Create mission → ingest document subset
- [ ] Query returns grounded snippet with citation
- [ ] Reranker rejects low-confidence match and surfaces fallback
- [ ] Filtering by aircraft type works
- [ ] Cache hit path works offline (airplane mode test)

### Real-Time Collaboration:

- [ ] Two browsers see same transcript updates instantly
- [ ] Agent state updates broadcast in <150 ms
- [ ] Supervisor annotation appears for operator within <400 ms
- [ ] Mission note locking works across users
- [ ] Lock auto-releases after idle timeout

### Presence & Pointer System:

- [ ] Pointers show for every user
- [ ] Colors remain consistent after reconnect
- [ ] Users removed from list instantly after disconnect (onDisconnect)

### Persistence:

- [ ] All users leave session → data remains in Postgres
- [ ] Refresh mid-response retains history + pending task list
- [ ] Offline queue flushes once connectivity returns

### Performance:

- [ ] Maintain 60 FPS UI with 100 transcript items
- [ ] 30 concurrent voice sessions do not exceed CPU/mem budgets
- [ ] Redis/WS usage stays within plan limits during soak test

---

## Risk Mitigation

**Biggest Risk:** Hybrid RAG drift leading to hallucinations.  
**Mitigation:** Enforce RRF fusion + reranker threshold + “No grounded answer” fallback; nightly eval harness comparing sqlite-vec vs pgvector parity.

**Second Risk:** Android always-on service killed by OEM battery managers.  
**Mitigation:** Mandatory onboarding to whitelist app, heartbeat watchdog, restart via BootReceiver.

**Third Risk:** Network drop during mission causes data loss.  
**Mitigation:** Local sqlite-vec + Couchbase Lite queue storing transcripts until sync; explicit offline banners.

**Fourth Risk:** Latency spikes from LLM provider outages.  
**Mitigation:** Multi-provider router (Gemini + Claude + local GGUF) with health probes; degrade gracefully to cached answers.
