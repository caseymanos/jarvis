from typing import List, Dict
import time
from app.models.document import Document, SearchResult, SearchQuery, RetrievalResponse
from app.services.bm25_retriever import BM25Retriever
from app.services.vector_retriever import VectorRetriever
from app.services.reranker import CrossEncoderReranker
from app.core.config import get_settings

settings = get_settings()


class HybridRetriever:
    def __init__(self):
        self.bm25_retriever = BM25Retriever()
        self.vector_retriever = VectorRetriever()
        self.reranker = CrossEncoderReranker()

    def initialize(self):
        """Initialize vector database table."""
        self.vector_retriever.create_vector_table()

    def index_documents(self, documents: List[Document]) -> None:
        """Index documents in both BM25 and vector stores."""
        # Index in BM25
        self.bm25_retriever.index_documents(documents)

        # Index in vector store
        self.vector_retriever.index_documents(documents)

    def _rrf_fusion(
        self,
        bm25_results: List[SearchResult],
        vector_results: List[SearchResult],
        k: int = 60
    ) -> List[SearchResult]:
        """
        Reciprocal Rank Fusion (RRF) to combine BM25 and vector search results.

        Formula: RRF_score = sum(1 / (k + rank_i))
        where k is a constant (typically 60) and rank_i is the rank from each retriever.
        """
        # Create score maps
        doc_scores: Dict[str, float] = {}
        doc_objects: Dict[str, SearchResult] = {}

        # Add BM25 scores
        for rank, result in enumerate(bm25_results, start=1):
            doc_id = result.id
            rrf_score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            doc_objects[doc_id] = result

        # Add vector scores
        for rank, result in enumerate(vector_results, start=1):
            doc_id = result.id
            rrf_score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
            if doc_id not in doc_objects:
                doc_objects[doc_id] = result

        # Sort by combined RRF score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Create results with RRF scores
        fused_results = []
        for doc_id, rrf_score in sorted_docs:
            result = doc_objects[doc_id]
            result.score = rrf_score  # Update with RRF score
            fused_results.append(result)

        return fused_results

    def search(self, search_query: SearchQuery) -> RetrievalResponse:
        """
        Hybrid search using BM25 + Vector + RRF + Reranking.
        """
        start_time = time.time()

        query = search_query.query
        top_k = search_query.top_k

        # Step 1: Retrieve from both BM25 and vector stores
        bm25_results = self.bm25_retriever.search(
            query,
            top_k=settings.bm25_top_k
        )

        vector_results = self.vector_retriever.search(
            query,
            top_k=settings.vector_top_k
        )

        # Step 2: Fuse results using RRF
        fused_results = self._rrf_fusion(bm25_results, vector_results)

        # Step 3: Rerank using cross-encoder
        reranked_results = self.reranker.rerank_deterministic(
            query,
            fused_results,
            top_k=settings.rerank_top_k
        )

        # If no results pass threshold, return empty
        if not reranked_results:
            reranked_results = []

        # Limit to requested top_k
        final_results = reranked_results[:top_k]

        retrieval_time_ms = (time.time() - start_time) * 1000

        return RetrievalResponse(
            query=query,
            results=final_results,
            total_results=len(final_results),
            retrieval_time_ms=retrieval_time_ms,
            method="hybrid"
        )

    def search_bm25_only(self, query: str, top_k: int = 5) -> RetrievalResponse:
        """BM25-only search for comparison."""
        start_time = time.time()
        results = self.bm25_retriever.search(query, top_k=top_k)
        retrieval_time_ms = (time.time() - start_time) * 1000

        return RetrievalResponse(
            query=query,
            results=results,
            total_results=len(results),
            retrieval_time_ms=retrieval_time_ms,
            method="bm25"
        )

    def search_vector_only(self, query: str, top_k: int = 5) -> RetrievalResponse:
        """Vector-only search for comparison."""
        start_time = time.time()
        results = self.vector_retriever.search(query, top_k=top_k)
        retrieval_time_ms = (time.time() - start_time) * 1000

        return RetrievalResponse(
            query=query,
            results=results,
            total_results=len(results),
            retrieval_time_ms=retrieval_time_ms,
            method="vector"
        )
