from rank_bm25 import BM25Okapi
from typing import List, Dict
import re
from app.models.document import Document, SearchResult


class BM25Retriever:
    def __init__(self):
        self.corpus: List[Document] = []
        self.bm25: BM25Okapi = None
        self.tokenized_corpus: List[List[str]] = []

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - split on whitespace and punctuation."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    def index_documents(self, documents: List[Document]) -> None:
        """Index documents for BM25 retrieval."""
        self.corpus = documents
        self.tokenized_corpus = [
            self._tokenize(f"{doc.title} {doc.content}")
            for doc in documents
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """Search using BM25 algorithm."""
        if not self.bm25:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # Get top k results
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include documents with non-zero scores
                doc = self.corpus[idx]
                results.append(SearchResult(
                    id=doc.id,
                    title=doc.title,
                    content=doc.content,
                    source=doc.source,
                    score=float(scores[idx]),
                    metadata=doc.metadata
                ))

        return results

    def get_document_count(self) -> int:
        """Return the number of indexed documents."""
        return len(self.corpus)
