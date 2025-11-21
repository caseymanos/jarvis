#!/usr/bin/env python3
"""
Quick test to verify Jarvis components are working.
Tests RAG retrieval + LLM response generation.
"""
import asyncio
import sys
from app.services.hybrid_retriever import HybridRetriever
from app.services.llm_service import get_llm_service
from app.models.document import Document, SearchQuery

async def quick_test():
    print("🧪 JARVIS QUICK TEST")
    print("=" * 60)

    try:
        # 1. Test Retriever
        print("\n1️⃣  Testing Document Retrieval System...")
        retriever = HybridRetriever()
        retriever.initialize()

        # Add sample doc
        sample_docs = [
            Document(
                id="test-1",
                title="Emergency Procedures",
                content="In case of engine failure, maintain 200 knots airspeed and attempt restart.",
                source="Test Manual",
                metadata={"type": "test"}
            )
        ]
        retriever.index_documents(sample_docs)
        print("   ✅ Retriever initialized and documents indexed")

        # Test search
        result = retriever.search(SearchQuery(query="what to do if engine fails", top_k=1))
        print(f"   ✅ Search works! Found {result.total_results} documents")

        # 2. Test LLM
        print("\n2️⃣  Testing LLM Response Generation...")
        llm_service = get_llm_service()

        response = await llm_service.generate_response(
            user_query="What should I do if my engine fails?",
            retrieved_context="[Test Manual] Emergency Procedures\nIn case of engine failure, maintain 200 knots airspeed and attempt restart.",
            session_id="test"
        )

        print(f"   ✅ LLM works! Model: {response['model']}")
        print(f"\n   Response: {response['text'][:150]}...")

        print("\n" + "=" * 60)
        print("✅ ALL SYSTEMS OPERATIONAL!")
        print("=" * 60)
        print("\nYou can now:")
        print("  1. Open http://localhost:3000")
        print("  2. Start a voice session")
        print("  3. Speak and Jarvis will respond!\n")

        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("  - Docker containers are running: docker compose ps")
        print("  - .env file has OPENAI_API_KEY set")
        print("  - Database is accessible")
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)
