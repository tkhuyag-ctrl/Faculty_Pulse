"""
Faculty Pulse Chatbot
A conversational interface for querying Haverford College faculty database
"""
import os
from typing import List, Dict, Optional, Union
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

        # Get available departments and content types for smart filtering
        stats = self.get_database_stats()
        self.available_departments = stats['departments']
        self.available_content_types = list(stats['content_types'].keys())

    def extract_filters_from_query(self, query: str, provided_department: Optional[str] = None,
                                   provided_content_type: Optional[str] = None):
        """
        Intelligently extract department, content type, and temporal filters from natural language query

        Args:
            query: User's natural language query
            provided_department: Department filter from UI (takes precedence)
            provided_content_type: Content type filter from UI (takes precedence)

        Returns:
            Tuple of (department, content_type, year_filter, temporal_context)
        """
        query_lower = query.lower()

        # If filters already provided via UI, use those
        department = provided_department
        content_type = provided_content_type

        # Department abbreviations and keywords mapping
        dept_keywords = {
            'Mathematics': ['math', 'mathematics', 'maths'],
            'Physics': ['physics', 'physical'],
            'Chemistry': ['chem', 'chemistry', 'chemical'],
            'Biology': ['bio', 'biology', 'biological'],
            'Computer Science': ['cs', 'computer science', 'computing', 'compsci'],
            'Psychology': ['psych', 'psychology', 'psychological'],
            'English': ['english', 'literature'],
            'History': ['history', 'historical'],
            'Economics': ['econ', 'economics', 'economic'],
            'Political Science': ['poli sci', 'political science', 'politics', 'polisci'],
            'Sociology': ['soc', 'sociology', 'sociological'],
            'Anthropology': ['anthro', 'anthropology'],
            'Philosophy': ['phil', 'philosophy'],
            'Linguistics': ['ling', 'linguistics'],
            'Music': ['music', 'musical'],
            'Religion': ['religion', 'religious'],
        }

        # Extract department if not provided
        if not department:
            for dept in self.available_departments:
                # Check exact department name match
                if dept.lower() in query_lower:
                    department = dept
                    break

                # Check keyword matches
                if dept in dept_keywords:
                    for keyword in dept_keywords[dept]:
                        # Match whole words or at word boundaries
                        if f' {keyword} ' in f' {query_lower} ' or query_lower.startswith(keyword + ' ') or query_lower.endswith(' ' + keyword):
                            department = dept
                            break
                    if department:
                        break

        # Extract content type if not provided
        # IMPORTANT: Be conservative - only filter content type when explicitly asking ABOUT that type
        # Don't filter when asking "who would be good FOR a talk" (wants all content to assess expertise)
        if not content_type:
            # Publications - clear intent to see research
            if any(word in query_lower for word in ['publication', 'paper', 'article', 'published', 'publish']):
                content_type = 'Publication'
            # Awards - clear intent to see honors
            elif any(word in query_lower for word in ['award', 'prize', 'honor', 'grant', 'fellowship']):
                content_type = 'Award'
            # Talks - ONLY filter if clearly asking about past talks (not "for a talk", "give a talk")
            # Check for phrases indicating PAST talks vs FUTURE potential
            elif any(phrase in query_lower for phrase in ['gave a talk', 'given talks', 'spoke at', 'speaking at', 'presented at']):
                content_type = 'Talk'
            # Don't filter for: "for a talk", "give a talk", "best for talk" - these want ALL data to assess expertise

        # Extract year filter and temporal context
        import re
        year_filter = None
        temporal_context = None

        # Look for specific years (2020-2026)
        years = re.findall(r'\b(202[0-6])\b', query)
        if years:
            year_filter = years[0]  # Use the first year found
            temporal_context = f"year_{year_filter}"
            print(f"[YEAR] Year filter extracted: {year_filter}")

        # Check for temporal keywords indicating recent/old
        elif 'recent' in query_lower or 'latest' in query_lower or 'newest' in query_lower or 'new' in query_lower:
            from datetime import datetime
            current_year = datetime.now().year
            temporal_context = "recent"
            # For "recent", use current year and previous 2 years for better coverage
            year_filter = [str(current_year), str(current_year - 1), str(current_year - 2)]
            print(f"[YEAR] Temporal context: RECENT - filtering for {year_filter}")
        elif 'old' in query_lower or 'oldest' in query_lower or 'earlier' in query_lower:
            temporal_context = "old"
            # For "old", we'll use 2020-2022 (earlier years in our dataset)
            year_filter = ["2020", "2021", "2022"]  # List of years to match
            print(f"[YEAR] Temporal context: OLD - filtering for 2020-2022")

        return department, content_type, year_filter, temporal_context

    def query_database(
        self,
        query: str,
        n_results: int = 5,
        content_type: Optional[str] = None,
        department: Optional[str] = None,
        year_filter: Optional[Union[str, List[str]]] = None
    ) -> Dict:
        """
        Query the vector database with semantic and metadata filtering

        Args:
            query: User query string
            n_results: Number of results to retrieve
            content_type: Optional filter by content type
            department: Optional filter by department
            year_filter: Optional year filter - single year string or list of years

        Returns:
            Dictionary with query results
        """
        # Enhance query for better semantic matching
        import re
        cleaned_query = query

        # Strip temporal keywords - they don't help semantic search
        temporal_words = ['recent', 'recently', 'latest', 'newest', 'new', 'current', 'old', 'oldest']
        for word in temporal_words:
            cleaned_query = re.sub(rf'\b{word}\b', '', cleaned_query, flags=re.IGNORECASE)

        # Enhance "best for talk" type queries to focus on expertise/achievements
        # Instead of searching for "best for a talk", search for "expert research achievements"
        if re.search(r'\b(best|good|suitable|recommend|top)\b.*\b(for|give|giving)\b.*\b(talk|presentation|lecture)', query, re.IGNORECASE):
            # Keep the department if specified
            dept_match = re.search(r'\bin\s+(\w+)', query, re.IGNORECASE)
            if dept_match:
                dept = dept_match.group(1)
                cleaned_query = f"{dept} faculty expert research achievements publications"
            else:
                cleaned_query = "faculty expert research achievements publications"
            print(f"[QUERY ENHANCEMENT] Detected 'best for talk' query - enhanced to search for expertise")

        # Clean up extra spaces
        cleaned_query = ' '.join(cleaned_query.split())

        # If query becomes empty after cleaning, use original
        if not cleaned_query.strip():
            cleaned_query = query

        print(f"\n{'='*60}")
        print(f"[DATABASE QUERY]")
        print(f"Original query: {query}")
        if cleaned_query != query:
            print(f"Cleaned query (temporal words removed): {cleaned_query}")
        print(f"n_results: {n_results}")
        print(f"content_type: {content_type}")
        print(f"department: {department}")
        if year_filter:
            print(f"year_filter: {year_filter}")

        results = self.db_manager.query_submissions(
            query_text=cleaned_query,  # Use cleaned query for better semantic matching
            n_results=n_results,
            content_type=content_type,
            department=department,
            year_filter=year_filter  # Add year filter for temporal queries
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

        system_prompt = """You are an expert research assistant for the Faculty Pulse system at Haverford College.
Your role is to provide comprehensive, detailed answers about faculty members, their publications, awards, talks, and research.

IMPORTANT GUIDELINES:

1. **Be Detailed and Thorough**: Provide rich, informative responses with specific details from the database
2. **Structure Your Response**: Use clear organization with sections, bullet points, or numbered lists when appropriate
3. **Include All Relevant Information**:
   - Faculty names and departments
   - Specific titles of publications/awards/talks
   - Dates and years
   - Dollar amounts for grants
   - Key details and descriptions
   - Source links when available

4. **Context and Analysis**:
   - Explain the significance of achievements
   - Provide context about awards and grants
   - Connect related information together
   - Identify patterns or themes across faculty work

5. **Comprehensive Coverage**: If multiple relevant results exist, discuss all of them, not just one or two

6. **Formatting**: Use markdown formatting for better readability:
   - **Bold** for faculty names and important terms
   - Bullet points for lists
   - Clear paragraph breaks

7. **Accuracy**: ONLY use information from the database results provided. Do NOT make up or infer information not present.

8. **Temporal Queries**: When users ask about "recent" or "latest" items:
   - Results are ranked by semantic relevance, NOT by date
   - Check the dates in the metadata and mention the most recent items you find
   - If no recent items appear in the results, acknowledge this limitation

9. **Helpful Tone**: Be professional, informative, and enthusiastic about faculty achievements."""

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

        # Call Claude API with Haiku (reliable, fast model)
        response = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            timeout=60.0  # 60 second timeout to prevent hangs
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

        # Intelligently extract filters from the query
        smart_department, smart_content_type, year_filter, temporal_context = self.extract_filters_from_query(
            user_query, department, content_type
        )

        print(f"\n[SMART FILTER EXTRACTION]")
        print(f"Original filters - Department: {department}, Content Type: {content_type}")
        print(f"Extracted filters - Department: {smart_department}, Content Type: {smart_content_type}")
        if year_filter:
            print(f"Year filter: {year_filter} (context: {temporal_context})")

        # Query the database with smart filters including year
        db_results = self.query_database(
            query=user_query,
            n_results=n_results,
            content_type=smart_content_type,
            department=smart_department,
            year_filter=year_filter
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
