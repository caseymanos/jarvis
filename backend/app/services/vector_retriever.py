from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from app.models.document import Document, SearchResult
from app.core.config import get_settings

settings = get_settings()


class VectorRetriever:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        self.model = SentenceTransformer(self.model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def get_connection(self):
        """Get database connection."""
        return psycopg2.connect(settings.database_url)

    def create_vector_table(self):
        """Create table with pgvector extension."""
        conn = self.get_connection()
        cur = conn.cursor()

        # Enable pgvector extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # Create documents table with vector column
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                metadata JSONB DEFAULT '{{}}',
                embedding vector({self.dimension}),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create index for faster vector search
        cur.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)

        conn.commit()
        cur.close()
        conn.close()

    def encode(self, text: str) -> List[float]:
        """Generate embedding for text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def index_documents(self, documents: List[Document]) -> None:
        """Index documents with embeddings."""
        conn = self.get_connection()
        cur = conn.cursor()

        # Generate embeddings and prepare data
        data = []
        for doc in documents:
            if doc.embedding is None:
                embedding = self.encode(f"{doc.title} {doc.content}")
            else:
                embedding = doc.embedding

            data.append((
                doc.id,
                doc.title,
                doc.content,
                doc.source,
                doc.metadata,
                embedding
            ))

        # Bulk insert
        execute_values(
            cur,
            """
            INSERT INTO documents (id, title, content, source, metadata, embedding)
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                source = EXCLUDED.source,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding
            """,
            data,
            template="(%s, %s, %s, %s, %s, %s::vector)"
        )

        conn.commit()
        cur.close()
        conn.close()

    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        """Search using vector similarity."""
        query_embedding = self.encode(query)

        conn = self.get_connection()
        cur = conn.cursor()

        # Cosine similarity search
        cur.execute(
            """
            SELECT id, title, content, source, metadata,
                   1 - (embedding <=> %s::vector) as similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, query_embedding, top_k)
        )

        results = []
        for row in cur.fetchall():
            results.append(SearchResult(
                id=row[0],
                title=row[1],
                content=row[2],
                source=row[3],
                score=float(row[5]),  # similarity score
                metadata=row[4] or {}
            ))

        cur.close()
        conn.close()

        return results

    def get_document_count(self) -> int:
        """Return the number of indexed documents."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
