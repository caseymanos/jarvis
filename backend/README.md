# Jarvis Backend - Hybrid Retrieval System

FastAPI backend implementing zero-hallucination hybrid RAG with BM25 + Vector Search + Cross-Encoder Reranking.

## Features

- **Hybrid Retrieval**: Combines BM25 (lexical) and vector search (semantic)
- **RRF Fusion**: Reciprocal Rank Fusion to merge results
- **Cross-Encoder Reranking**: Int8 quantized model with 0.88 threshold
- **Deterministic Results**: Rejects low-confidence snippets
- **Socket.IO Support**: Ready for real-time voice streaming

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Database

You need PostgreSQL with pgvector extension. Use the same database as the web app.

**Option 1: Neon (Recommended)**
- Sign up at https://neon.tech
- Create project
- Copy connection string

**Option 2: Local PostgreSQL**
```bash
brew install postgresql@15
brew services start postgresql@15
createdb jarvis
psql jarvis -c "CREATE EXTENSION vector;"
```

### 4. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Update `DATABASE_URL` with your connection string.

### 5. Run Server

```bash
python -m app.main
```

Server will start on http://localhost:8000

## API Endpoints

### Retrieval

**POST /retrieval/search** - Hybrid search (BM25 + Vector + Rerank)
```json
{
  "query": "How do I check hydraulic pressure?",
  "top_k": 5
}
```

**POST /retrieval/search/bm25** - BM25-only search
**POST /retrieval/search/vector** - Vector-only search

### Indexing

**POST /retrieval/index** - Index documents
```json
[
  {
    "id": "doc_001",
    "title": "Document Title",
    "content": "Document content...",
    "source": "Source Name",
    "metadata": {"key": "value"}
  }
]
```

### Stats

**GET /retrieval/stats** - Get system statistics

## Testing

```bash
# Start server first
python -m app.main

# In another terminal
python test_retrieval.py
```

## Architecture

```
Query
  ↓
[BM25 Retrieval] + [Vector Search]
  ↓
Reciprocal Rank Fusion (RRF)
  ↓
Cross-Encoder Reranking
  ↓
Threshold Filter (≥ 0.88)
  ↓
Results or "No grounded answer"
```

## Key Components

- **BM25Retriever** (`app/services/bm25_retriever.py`) - Lexical search using rank-bm25
- **VectorRetriever** (`app/services/vector_retriever.py`) - Semantic search with pgvector
- **CrossEncoderReranker** (`app/services/reranker.py`) - Int8 quantized reranking
- **HybridRetriever** (`app/services/hybrid_retriever.py`) - Combines all methods

## Models Used

- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (int8 quantized)

## Configuration

Edit `.env` to customize:

```bash
# Retrieval parameters
BM25_TOP_K=20           # Top K from BM25
VECTOR_TOP_K=20         # Top K from vector search
RERANK_TOP_K=5          # Top K after reranking
RERANKER_THRESHOLD=0.88 # Minimum reranker score
```

## Next Steps

- [ ] Integrate with voice transcription
- [ ] Add LLM response generation
- [ ] Implement document upload endpoint
- [ ] Add mission-scoped filtering
- [ ] Connect to Temporal for workflow management
