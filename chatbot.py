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
        results = self.db_manager.query_submissions(
            query_text=query,
            n_results=n_results,
            content_type=content_type,
            department=department
        )
        return results

    def format_database_results(self, results: Dict) -> str:
        """
        Format database results into a readable string for the LLM

        Args:
            results: ChromaDB query results

        Returns:
            Formatted string with results
        """
        if not results['ids'] or len(results['ids'][0]) == 0:
            return "No relevant information found in the database."

        formatted = "Here is the relevant information from the faculty database:\n\n"

        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        ), 1):
            formatted += f"[Result {i} - Relevance: {1-distance:.2f}]\n"
            formatted += f"Faculty: {metadata['faculty_name']}\n"
            formatted += f"Department: {metadata['department']}\n"
            formatted += f"Type: {metadata['content_type']}\n"
            formatted += f"Date: {metadata['date_published']}\n"
            formatted += f"Content: {doc[:500]}{'...' if len(doc) > 500 else ''}\n"
            formatted += "-" * 80 + "\n\n"

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

        # Call Claude API
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        assistant_response = response.content[0].text

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
        # Query the database
        db_results = self.query_database(
            query=user_query,
            n_results=n_results,
            content_type=content_type,
            department=department
        )

        # Format results for LLM
        formatted_results = self.format_database_results(db_results)

        # Generate natural language response
        response = self.generate_response(user_query, formatted_results)

        return {
            "response": response,
            "database_results": db_results,
            "num_results": len(db_results['ids'][0]) if db_results['ids'] else 0
        }

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
