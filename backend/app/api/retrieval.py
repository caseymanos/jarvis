from fastapi import APIRouter, HTTPException
from typing import List
from app.models.document import Document, SearchQuery, RetrievalResponse
from app.services.hybrid_retriever import HybridRetriever

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

# Global retriever instance
retriever = HybridRetriever()


@router.on_event("startup")
async def startup_event():
    """Initialize retriever on startup."""
    retriever.initialize()


@router.post("/search", response_model=RetrievalResponse)
async def search(query: SearchQuery):
    """
    Hybrid search endpoint using BM25 + Vector + RRF + Reranking.

    Returns results only if reranker score >= 0.88 threshold.
    If all results rejected, returns empty list (no grounded answer).
    """
    try:
        response = retriever.search(query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/bm25", response_model=RetrievalResponse)
async def search_bm25(query: SearchQuery):
    """BM25-only search for comparison/debugging."""
    try:
        response = retriever.search_bm25_only(query.query, query.top_k)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/vector", response_model=RetrievalResponse)
async def search_vector(query: SearchQuery):
    """Vector-only search for comparison/debugging."""
    try:
        response = retriever.search_vector_only(query.query, query.top_k)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index", status_code=201)
async def index_documents(documents: List[Document]):
    """
    Index documents for retrieval.

    Indexes documents in both BM25 and vector stores.
    """
    try:
        retriever.index_documents(documents)
        return {
            "message": f"Successfully indexed {len(documents)} documents",
            "count": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get retrieval system statistics."""
    try:
        bm25_count = retriever.bm25_retriever.get_document_count()
        vector_count = retriever.vector_retriever.get_document_count()

        return {
            "bm25_documents": bm25_count,
            "vector_documents": vector_count,
            "reranker_threshold": retriever.reranker.threshold,
            "reranker_model": retriever.reranker.model_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
