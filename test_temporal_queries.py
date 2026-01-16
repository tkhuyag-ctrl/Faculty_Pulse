"""
Test script for temporal queries
"""
import os
import sys
from dotenv import load_dotenv
from chatbot import FacultyPulseChatbot

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_temporal_queries():
    """Test temporal query functionality"""

    # Load environment variables
    load_dotenv()

    # Initialize chatbot
    print("Initializing chatbot...")
    api_key = os.getenv('ANTHROPIC_API_KEY')
    chatbot = FacultyPulseChatbot(api_key=api_key, persist_directory="./chroma_db")

    # Test queries with temporal keywords
    test_queries = [
        "What are the recent publications?",
        "Show me the latest research",
        "What are the oldest publications?",
        "Tell me about publications from 2024"
    ]

    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"TESTING QUERY: {query}")
        print('='*80)

        try:
            response, num_results = chatbot.chat(query, n_results=3)
            print(f"\n[SUCCESS] Got response with {num_results} results")
            print(f"\nResponse preview (first 500 chars):")
            print(response[:500] + "..." if len(response) > 500 else response)
        except Exception as e:
            print(f"\n[FAILED] Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_temporal_queries()
