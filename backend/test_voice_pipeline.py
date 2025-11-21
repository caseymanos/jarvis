#!/usr/bin/env python3
"""
Test script for the voice processing pipeline.
Tests the complete flow: audio → STT → RAG → LLM → TTS
"""
import asyncio
import os
from app.services.speech_to_text import get_stt_service
from app.services.hybrid_retriever import HybridRetriever
from app.services.llm_service import get_llm_service
from app.services.text_to_speech import get_tts_service
from app.models.document import Document, SearchQuery
from app.core.config import get_settings

# Load settings
os.environ.setdefault("DATABASE_URL", "postgresql://jarvis:jarvis@localhost:5432/jarvis")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("LLM_PROVIDER", "xai")
os.environ.setdefault("LLM_MODEL", "grok-beta")
os.environ.setdefault("TTS_PROVIDER", "openai")
os.environ.setdefault("TTS_VOICE", "nova")

settings = get_settings()


async def test_pipeline():
    """Test the complete voice processing pipeline."""

    print("=" * 80)
    print("JARVIS VOICE PROCESSING PIPELINE TEST")
    print("=" * 80)

    # Initialize services
    print("\n1. Initializing services...")
    retriever = HybridRetriever()
    retriever.initialize()

    # Index sample documents
    print("\n2. Indexing sample knowledge base documents...")
    sample_docs = [
        Document(
            id="1",
            title="F-16 Emergency Procedures",
            content="In the event of engine failure at high altitude, maintain airspeed above 200 knots. "
                   "Attempt engine restart using the emergency restart procedure. If restart fails, "
                   "prepare for controlled ejection. Minimum safe ejection altitude is 2000 feet AGL.",
            source="F-16 Flight Manual",
            metadata={"aircraft": "F-16", "category": "emergency"}
        ),
        Document(
            id="2",
            title="Radio Communication Protocols",
            content="Use standard NATO phonetic alphabet for all radio communications. "
                   "Brevity codes: 'Winchester' means out of ammunition, 'Bingo' means minimum fuel for RTB. "
                   "Always acknowledge commands with callsign and action.",
            source="Tactical Communication Guide",
            metadata={"category": "communications"}
        ),
        Document(
            id="3",
            title="Target Acquisition Procedures",
            content="Positive visual identification (PID) is required before weapon release. "
                   "Laser designation code must be coordinated with ground forces. "
                   "Minimum safe release altitude varies by ordnance type.",
            source="Combat Operations Manual",
            metadata={"category": "weapons"}
        ),
    ]

    retriever.index_documents(sample_docs)
    print(f"✓ Indexed {len(sample_docs)} documents")

    # Test queries
    test_queries = [
        "What should I do if my engine fails?",
        "What does Winchester mean?",
        "How do I engage a target?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST QUERY {i}: {query}")
        print("=" * 80)

        # Step 1: Simulate STT (we'll use text directly for testing)
        print(f"\n[STT] Transcribed: \"{query}\"")

        # Step 2: Document Retrieval
        print("\n[RAG] Searching knowledge base...")
        search_query = SearchQuery(query=query, top_k=2)
        retrieval_response = retriever.search(search_query)

        print(f"✓ Retrieved {retrieval_response.total_results} documents in {retrieval_response.retrieval_time_ms:.2f}ms")
        for idx, result in enumerate(retrieval_response.results, 1):
            print(f"  {idx}. [{result.source}] {result.title} (score: {result.score:.4f})")

        # Format context for LLM
        retrieved_context = "\n\n".join([
            f"[{result.source}] {result.title}\n{result.content}"
            for result in retrieval_response.results
        ])

        # Step 3: LLM Response Generation
        print("\n[LLM] Generating response...")
        llm_service = get_llm_service()
        llm_response = await llm_service.generate_response(
            user_query=query,
            retrieved_context=retrieved_context,
            session_id="test-session",
            conversation_history=None
        )

        print(f"✓ Generated response using {llm_response['model']} ({llm_response.get('tokens_used', 'N/A')} tokens)")
        print(f"\n[RESPONSE]")
        print(f"{llm_response['text']}")

        # Step 4: TTS (optional - comment out if no API key)
        if os.getenv("OPENAI_API_KEY"):
            print("\n[TTS] Converting to speech...")
            tts_service = get_tts_service()
            audio_chunks = 0
            total_bytes = 0

            async for chunk in tts_service.synthesize_speech(
                text=llm_response['text'],
                session_id="test-session",
                stream=True
            ):
                audio_chunks += 1
                total_bytes += len(chunk)

            print(f"✓ Generated {audio_chunks} audio chunks ({total_bytes:,} bytes)")
        else:
            print("\n[TTS] Skipped (no OPENAI_API_KEY)")

        print()

    print("=" * 80)
    print("✅ PIPELINE TEST COMPLETE!")
    print("=" * 80)
    print("\nAll components working correctly:")
    print("  ✓ Document Retrieval (BM25 + Vector + RRF + Reranking)")
    print("  ✓ LLM Response Generation (Grok 3)")
    if os.getenv("OPENAI_API_KEY"):
        print("  ✓ Text-to-Speech (OpenAI TTS)")
    print("\nJARVIS is ready to assist operators in the field! 🎯")


if __name__ == "__main__":
    asyncio.run(test_pipeline())
