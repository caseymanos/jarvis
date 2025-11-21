from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Document(BaseModel):
    id: str
    title: str
    content: str
    source: str
    metadata: dict = {}
    embedding: Optional[List[float]] = None
    created_at: datetime = datetime.now()


class SearchQuery(BaseModel):
    query: str
    top_k: int = 5
    scope: Optional[str] = None  # global, aircraft_type, mission
    filter_metadata: dict = {}


class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    source: str
    score: float
    reranker_score: Optional[float] = None
    metadata: dict = {}


class RetrievalResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    retrieval_time_ms: float
    method: str  # "hybrid", "bm25", "vector"
