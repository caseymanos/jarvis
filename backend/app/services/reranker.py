from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import List, Tuple
from app.models.document import SearchResult
from app.core.config import get_settings

settings = get_settings()


class CrossEncoderReranker:
    def __init__(self, model_name: str = None, threshold: float = None):
        self.model_name = model_name or settings.reranker_model
        self.threshold = threshold or settings.reranker_threshold

        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

        # Use int8 quantization for efficiency
        self.model = torch.quantization.quantize_dynamic(
            self.model,
            {torch.nn.Linear},
            dtype=torch.qint8
        )

        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(self.device)

    def score_pair(self, query: str, document: str) -> float:
        """Score a query-document pair."""
        inputs = self.tokenizer(
            query,
            document,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            score = torch.sigmoid(logits).item()

        return score

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = None
    ) -> Tuple[List[SearchResult], List[SearchResult]]:
        """
        Rerank results using cross-encoder.

        Returns:
            Tuple of (accepted_results, rejected_results)
        """
        if not results:
            return [], []

        # Score all results
        scored_results = []
        for result in results:
            # Combine title and content for scoring
            document_text = f"{result.title}: {result.content}"
            reranker_score = self.score_pair(query, document_text)

            result.reranker_score = reranker_score
            scored_results.append(result)

        # Sort by reranker score
        scored_results.sort(key=lambda x: x.reranker_score, reverse=True)

        # Apply threshold
        accepted = [r for r in scored_results if r.reranker_score >= self.threshold]
        rejected = [r for r in scored_results if r.reranker_score < self.threshold]

        # Apply top_k if specified
        if top_k is not None:
            accepted = accepted[:top_k]

        return accepted, rejected

    def rerank_deterministic(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = None
    ) -> List[SearchResult]:
        """
        Deterministic reranking - only return results above threshold.
        Returns "No grounded answer" behavior if all results rejected.
        """
        accepted, rejected = self.rerank(query, results, top_k)

        if not accepted:
            # All results below threshold
            return []

        return accepted
