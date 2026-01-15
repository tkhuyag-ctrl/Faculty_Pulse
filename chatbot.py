"""
Faculty Pulse Chatbot
A conversational interface for querying Haverford College faculty database
"""
import os
from typing import List, Dict, Optional
from chroma_manager import ChromaDBManager
from anthropic import Anthropic


class FacultyPulseChatbot:
    """Chatbot for querying faculty database with natural language responses"""

    def __init__(self, api_key: Optional[str] = None, persist_directory: str = "./chroma_db"):
        """
        Initialize the chatbot

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env variable)
            persist_directory: ChromaDB persistence directory
        """
        self.db_manager = ChromaDBManager(persist_directory=persist_directory)

        # Initialize Anthropic client
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key, timeout=60.0)
        self.conversation_history = []

    def query_database(
        self,
        query: str,
        n_results: int = 5,
        content_type: Optional[str] = None,
        department: Optional[str] = None
    ) -> Dict:
        """
        Query the vector database

        Args:
            query: User query string
            n_results: Number of results to retrieve
            content_type: Optional filter by content type
            department: Optional filter by department

        Returns:
            Dictionary with query results
        """
        print(f"\n{'='*60}")
        print(f"[DATABASE QUERY]")
        print(f"Query: {query}")
        print(f"n_results: {n_results}")
        print(f"content_type: {content_type}")
        print(f"department: {department}")

        results = self.db_manager.query_submissions(
            query_text=query,
            n_results=n_results,
            content_type=content_type,
            department=department
        )

        num_results = len(results['ids'][0]) if results['ids'] else 0
        print(f"\n[DATABASE RESULTS]")
        print(f"Number of results returned: {num_results}")
        if num_results > 0:
            print(f"\nTop results:")
            for i, (doc_id, metadata, distance) in enumerate(zip(
                results['ids'][0][:3],  # Show top 3
                results['metadatas'][0][:3],
                results['distances'][0][:3]
            ), 1):
                print(f"  {i}. ID: {doc_id}")
                print(f"     Faculty: {metadata['faculty_name']}")
                print(f"     Department: {metadata['department']}")
                print(f"     Type: {metadata['content_type']}")
                print(f"     Distance: {distance:.4f} (Relevance: {1-distance:.4f})")
                print(f"     Content preview: {results['documents'][0][i-1][:100]}...")
        else:
            print("  No results found")
        print(f"{'='*60}\n")

        return results

    def format_database_results(self, results: Dict, max_total_chars: int = 100000) -> str:
        """
        Format database results with intelligent adaptive truncation for RAG

        Args:
            results: ChromaDB query results
            max_total_chars: Maximum total characters to include (default 100K for Claude context)

        Returns:
            Formatted string with results
        """
        if not results['ids'] or len(results['ids'][0]) == 0:
            return "No relevant information found in the database."

        formatted = "Here is the relevant information from the faculty database:\n\n"
        total_chars = 0

        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            relevance = 1 - distance

            # Adaptive truncation based on relevance and remaining budget
            if relevance > 0.7 and total_chars < max_total_chars * 0.7:
                # High relevance: include more text (up to 30K chars for full PDFs)
                content_limit = min(30000, max_total_chars - total_chars - 1000)
            elif relevance > 0.5 and total_chars < max_total_chars * 0.9:
                # Medium relevance: include moderate text (up to 10K chars)
                content_limit = min(10000, max_total_chars - total_chars - 1000)
            elif relevance > 0.3:
                # Lower relevance: include basic text (up to 2K chars)
                content_limit = min(2000, max_total_chars - total_chars - 1000)
            else:
                # Very low relevance: minimal text (500 chars)
                content_limit = 500

            content = doc[:content_limit]
            truncated = len(doc) > content_limit

            formatted += f"[Result {i} - Relevance: {relevance:.2f}]\n"
            formatted += f"Faculty: {metadata['faculty_name']}\n"
            formatted += f"Department: {metadata['department']}\n"
            formatted += f"Type: {metadata['content_type']}\n"
            formatted += f"Date: {metadata['date_published']}\n"
            formatted += f"Content ({len(doc):,} chars total, showing {len(content):,}):\n"
            formatted += content
            if truncated:
                formatted += f"\n\n[Document truncated. Full document: {len(doc):,} characters]"
            formatted += "\n" + "-" * 80 + "\n\n"

            total_chars += len(content)

            # Stop if approaching the limit
            if total_chars > max_total_chars:
                formatted += f"\n[Additional results truncated to stay within context limits]\n"
                break

        return formatted

    def generate_response(self, user_query: str, database_results: str) -> str:
        """
        Generate a natural language response using Claude

        Args:
            user_query: Original user query
            database_results: Formatted database results

        Returns:
            Natural language response from Claude
        """
        print(f"\n[CLAUDE API CALL]")
        print(f"User query: {user_query}")
        print(f"Database context length: {len(database_results)} characters")
        print(f"Conversation history: {len(self.conversation_history)} messages")

        system_prompt = """You are a helpful assistant for the Faculty Pulse system at Haverford College.
Your role is to answer questions about faculty members, their publications, awards, and talks.

You will be provided with:
1. A user's question
2. Relevant information retrieved from the faculty database

Your task is to:
- Provide clear, concise answers based on the database information
- If the database has relevant information, synthesize it into a natural response
- If the database doesn't have relevant information, politely say so
- Cite specific faculty names, departments, and dates when relevant
- Be conversational and friendly
- If asked about multiple faculty or topics, organize your response clearly

Do NOT make up information that isn't in the database results."""

        # Build the conversation with context
        messages = self.conversation_history.copy()

        # Add the current query with database context
        current_message = f"""User Question: {user_query}

{database_results}

Based on the information above, please provide a helpful answer to the user's question."""

        messages.append({
            "role": "user",
            "content": current_message
        })

        print(f"Calling Claude API (model: claude-3-haiku-20240307)...")

        # Call Claude API
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,  # Increased for longer, detailed responses
            system=system_prompt,
            messages=messages
        )

        assistant_response = response.content[0].text

        print(f"\n[CLAUDE RESPONSE]")
        print(f"Response length: {len(assistant_response)} characters")
        print(f"Response preview: {assistant_response[:200]}...")
        print(f"API usage - Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")

        # Update conversation history (keep last 10 exchanges)
        self.conversation_history.append({"role": "user", "content": user_query})
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

        if len(self.conversation_history) > 20:  # 10 exchanges = 20 messages
            self.conversation_history = self.conversation_history[-20:]

        return assistant_response

    def chat(
        self,
        user_query: str,
        n_results: int = 5,
        content_type: Optional[str] = None,
        department: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Main chat function - queries database and generates response

        Args:
            user_query: User's question
            n_results: Number of database results to retrieve
            content_type: Optional filter by content type
            department: Optional filter by department

        Returns:
            Dictionary with response and metadata
        """
        print(f"\n{'#'*60}")
        print(f"# NEW CHAT REQUEST")
        print(f"{'#'*60}")

        # Query the database
        db_results = self.query_database(
            query=user_query,
            n_results=n_results,
            content_type=content_type,
            department=department
        )

        # Format results for LLM
        formatted_results = self.format_database_results(db_results)
        print(f"\n[FORMATTED RESULTS FOR CLAUDE]")
        print(f"Formatted results preview:\n{formatted_results[:500]}...")

        # Generate natural language response
        response = self.generate_response(user_query, formatted_results)

        result = {
            "response": response,
            "database_results": db_results,
            "num_results": len(db_results['ids'][0]) if db_results['ids'] else 0
        }

        print(f"\n[CHAT COMPLETE]")
        print(f"Returning {result['num_results']} results to user")
        print(f"{'#'*60}\n")

        return result

    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation_history = []

    def get_database_stats(self) -> Dict[str, any]:
        """Get statistics about the database"""
        total_count = self.db_manager.get_collection_count()

        # Get all submissions to analyze
        all_submissions = self.db_manager.get_all_submissions()

        stats = {
            "total_documents": total_count,
            "content_types": {},
            "departments": set()
        }

        if all_submissions['metadatas']:
            for metadata in all_submissions['metadatas']:
                # Count content types
                content_type = metadata['content_type']
                stats['content_types'][content_type] = stats['content_types'].get(content_type, 0) + 1

                # Collect departments
                stats['departments'].add(metadata['department'])

        stats['departments'] = sorted(list(stats['departments']))

        return stats


# Example usage
if __name__ == "__main__":
    """
    Simple command-line test of the chatbot
    """
    print("Faculty Pulse Chatbot - Test Mode")
    print("=" * 60)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it using: export ANTHROPIC_API_KEY='your-api-key'")
        exit(1)

    # Initialize chatbot
    chatbot = FacultyPulseChatbot()

    # Get database stats
    stats = chatbot.get_database_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total Documents: {stats['total_documents']}")
    print(f"  Content Types: {stats['content_types']}")
    print(f"  Departments: {', '.join(stats['departments'])}")

    # Test query
    print("\n" + "=" * 60)
    print("Test Query: 'What awards have faculty members received?'")
    print("=" * 60)

    result = chatbot.chat("What awards have faculty members received?")
    print(f"\nResponse:\n{result['response']}")
    print(f"\nFound {result['num_results']} relevant documents")
