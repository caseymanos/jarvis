"""
Test script for the hybrid retrieval system.
Run this after starting the server to test the retrieval functionality.
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_index_documents():
    """Test document indexing."""
    print("\n=== Testing Document Indexing ===")

    documents = [
        {
            "id": "doc_001",
            "title": "Aircraft Hydraulic System",
            "content": "The hydraulic system provides pressure for flight control surfaces. Normal operating pressure is 3000 PSI. Check hydraulic fluid levels during pre-flight inspection.",
            "source": "A320 Maintenance Manual",
            "metadata": {"aircraft_type": "A320", "section": "hydraulics"}
        },
        {
            "id": "doc_002",
            "title": "Engine Start Procedure",
            "content": "Before engine start, ensure all passengers are seated. Set parking brake. Turn on battery and external power. Start APU if needed. Monitor N1 and N2 gauges during start sequence.",
            "source": "Flight Operations Manual",
            "metadata": {"aircraft_type": "A320", "section": "procedures"}
        },
        {
            "id": "doc_003",
            "title": "Emergency Evacuation",
            "content": "In case of emergency evacuation, command EVACUATE three times. Ensure all exits are clear. Direct passengers to nearest exits. Verify cabin is clear before exiting.",
            "source": "Emergency Procedures Guide",
            "metadata": {"aircraft_type": "A320", "section": "emergency"}
        },
        {
            "id": "doc_004",
            "title": "Weather Minimums",
            "content": "Visual flight requires minimum 3 statute miles visibility and clear of clouds. IFR operations require published minimums for approach category. Check NOTAMs for temporary restrictions.",
            "source": "Operations Manual",
            "metadata": {"section": "weather"}
        },
        {
            "id": "doc_005",
            "title": "Fuel Management",
            "content": "Monitor fuel quantity and balance throughout flight. Normal fuel consumption is approximately 2400 kg/hour at cruise. Maintain minimum fuel reserves per regulations.",
            "source": "Flight Operations Manual",
            "metadata": {"aircraft_type": "A320", "section": "fuel"}
        }
    ]

    response = requests.post(f"{BASE_URL}/retrieval/index", json=documents)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_hybrid_search():
    """Test hybrid search."""
    print("\n=== Testing Hybrid Search ===")

    query = {
        "query": "How do I check hydraulic pressure?",
        "top_k": 3
    }

    response = requests.post(f"{BASE_URL}/retrieval/search", json=query)
    result = response.json()

    print(f"Query: {result['query']}")
    print(f"Method: {result['method']}")
    print(f"Retrieval time: {result['retrieval_time_ms']:.2f}ms")
    print(f"Results found: {result['total_results']}")

    for i, doc in enumerate(result['results'], 1):
        print(f"\n--- Result {i} ---")
        print(f"Title: {doc['title']}")
        print(f"Score: {doc['score']:.4f}")
        print(f"Reranker Score: {doc.get('reranker_score', 'N/A')}")
        print(f"Content: {doc['content'][:100]}...")


def test_bm25_search():
    """Test BM25-only search."""
    print("\n=== Testing BM25 Search ===")

    query = {
        "query": "engine start procedure",
        "top_k": 3
    }

    response = requests.post(f"{BASE_URL}/retrieval/search/bm25", json=query)
    result = response.json()

    print(f"Query: {result['query']}")
    print(f"Results: {result['total_results']}")
    for doc in result['results']:
        print(f"- {doc['title']} (score: {doc['score']:.4f})")


def test_vector_search():
    """Test vector-only search."""
    print("\n=== Testing Vector Search ===")

    query = {
        "query": "What should I do in an emergency?",
        "top_k": 3
    }

    response = requests.post(f"{BASE_URL}/retrieval/search/vector", json=query)
    result = response.json()

    print(f"Query: {result['query']}")
    print(f"Results: {result['total_results']}")
    for doc in result['results']:
        print(f"- {doc['title']} (score: {doc['score']:.4f})")


def test_no_grounded_answer():
    """Test query with no grounded answer."""
    print("\n=== Testing No Grounded Answer ===")

    query = {
        "query": "How to fly to Mars?",
        "top_k": 3
    }

    response = requests.post(f"{BASE_URL}/retrieval/search", json=query)
    result = response.json()

    print(f"Query: {result['query']}")
    print(f"Results: {result['total_results']}")
    if result['total_results'] == 0:
        print("✓ Correctly returned no results (all below threshold)")


def test_stats():
    """Test stats endpoint."""
    print("\n=== Testing Stats Endpoint ===")

    response = requests.get(f"{BASE_URL}/retrieval/stats")
    stats = response.json()

    print(f"BM25 documents: {stats['bm25_documents']}")
    print(f"Vector documents: {stats['vector_documents']}")
    print(f"Reranker threshold: {stats['reranker_threshold']}")
    print(f"Reranker model: {stats['reranker_model']}")


if __name__ == "__main__":
    print("Starting Retrieval System Tests...")
    print("Make sure the server is running: python -m app.main")

    try:
        # Test health endpoint
        response = requests.get(f"{BASE_URL}/health")
        print(f"\nServer health: {response.json()}")

        # Run tests
        test_index_documents()
        test_stats()
        test_hybrid_search()
        test_bm25_search()
        test_vector_search()
        test_no_grounded_answer()

        print("\n✓ All tests completed!")

    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to server")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Error: {e}")
