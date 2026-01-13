import chromadb
import json
from typing import List, Dict, Optional, Literal
from chromadb.config import Settings
from enum import Enum


class ContentType(Enum):
    """Enum for valid content types"""
    AWARD = "Award"
    PUBLICATION = "Publication"
    TALK = "Talk"


class ChromaDBManager:
    """Manager class for ChromaDB operations"""

    def __init__(self, persist_directory: str = "./chroma_db", collection_name: str = "faculty_pulse"):
        """
        Initialize ChromaDB client and collection

        Args:
            persist_directory: Directory to persist the database
            collection_name: Name of the collection to use
        """
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """
        Add documents to ChromaDB collection

        Args:
            documents: List of document texts
            metadatas: List of metadata dictionaries
            ids: List of unique document IDs
        """
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully added {len(documents)} documents to collection '{self.collection_name}'")

    def add_submission_from_json(self, json_file_path: str):
        """
        Add a single submission from a JSON file

        Args:
            json_file_path: Path to JSON file with a single submission

        Expected JSON format:
        {
            "id": "sub_001",
            "document": "Document content string",
            "metadata": {
                "faculty_name": "Dr. John Doe",
                "date_published": "2026-01-13T10:30:00Z",
                "content_type": "Award",
                "department": "Computer Science"
            }
        }
        """
        with open(json_file_path, 'r', encoding='utf-8') as f:
            submission = json.load(f)

        valid_content_types = {ct.value for ct in ContentType}

        # Validate content_type
        content_type = submission.get('metadata', {}).get('content_type')
        if content_type not in valid_content_types:
            raise ValueError(f"Invalid content_type '{content_type}' for submission {submission['id']}. Valid types: {valid_content_types}")

        self.collection.add(
            documents=[submission['document']],
            metadatas=[submission['metadata']],
            ids=[submission['id']]
        )
        print(f"Successfully added submission '{submission['id']}' to collection '{self.collection_name}'")

    def add_single_submission(
        self,
        submission_id: str,
        document: str,
        faculty_name: str,
        date_published: str,
        content_type: str,
        department: str
    ):
        """
        Add a single submission to the collection

        Args:
            submission_id: Unique submission ID
            document: Document text content
            faculty_name: Name of the faculty member
            date_published: Publication date in ISO 8601 format (e.g., "2026-01-13T10:30:00Z")
            content_type: Type of content - must be "Award", "Publication", or "Talk"
            department: Department name

        Raises:
            ValueError: If content_type is not valid
        """
        # Validate content_type
        valid_content_types = {ct.value for ct in ContentType}
        if content_type not in valid_content_types:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be one of: {valid_content_types}")

        metadata = {
            "faculty_name": faculty_name,
            "date_published": date_published,
            "content_type": content_type,
            "department": department
        }

        self.collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[submission_id]
        )
        print(f"Successfully added submission '{submission_id}' to collection")

    def query_submissions(self, query_text: str, n_results: int = 5,
                         content_type: Optional[str] = None,
                         department: Optional[str] = None):
        """
        Query submissions from the collection

        Args:
            query_text: Query text
            n_results: Number of results to return
            content_type: Optional filter by content type (Award, Publication, Talk)
            department: Optional filter by department

        Returns:
            Query results
        """
        where_filter = {}

        if content_type:
            where_filter["content_type"] = content_type

        if department:
            where_filter["department"] = department

        query_kwargs = {
            "query_texts": [query_text],
            "n_results": n_results
        }

        if where_filter:
            query_kwargs["where"] = where_filter

        results = self.collection.query(**query_kwargs)
        return results

    def get_collection_count(self):
        """Get the number of documents in the collection"""
        return self.collection.count()

    def delete_submission(self, submission_id: str):
        """Delete a submission by ID"""
        self.collection.delete(ids=[submission_id])
        print(f"Deleted submission '{submission_id}'")

    def update_submission(
        self,
        submission_id: str,
        document: str,
        faculty_name: str,
        date_published: str,
        content_type: str,
        department: str
    ):
        """
        Update an existing submission

        Args:
            submission_id: Unique submission ID
            document: Document text content
            faculty_name: Name of the faculty member
            date_published: Publication date in ISO 8601 format
            content_type: Type of content - must be "Award", "Publication", or "Talk"
            department: Department name

        Raises:
            ValueError: If content_type is not valid
        """
        # Validate content_type
        valid_content_types = {ct.value for ct in ContentType}
        if content_type not in valid_content_types:
            raise ValueError(f"Invalid content_type '{content_type}'. Must be one of: {valid_content_types}")

        metadata = {
            "faculty_name": faculty_name,
            "date_published": date_published,
            "content_type": content_type,
            "department": department
        }

        self.collection.update(
            ids=[submission_id],
            documents=[document],
            metadatas=[metadata]
        )
        print(f"Updated submission '{submission_id}'")


# Example usage
if __name__ == "__main__":
    # Initialize the manager
    manager = ChromaDBManager()

    # Example 1: Add submission from JSON file
    print("Adding submission from JSON file...")
    manager.add_submission_from_json("data_example.json")

    # Example 2: Add a single submission
    print("\nAdding a single submission...")
    manager.add_single_submission(
        submission_id="sub_006",
        document="Dr. Williams published a groundbreaking study on climate change adaptation strategies in coastal communities.",
        faculty_name="Dr. Jennifer Williams",
        date_published="2026-01-12T11:00:00Z",
        content_type="Publication",
        department="Environmental Science"
    )

    # Check collection count
    print(f"\nTotal submissions in collection: {manager.get_collection_count()}")

    # Query example - all submissions
    print("\nQuerying all submissions about 'award'...")
    results = manager.query_submissions("award", n_results=3)
    print(f"Query results: {results}")

    # Query with filters
    print("\nQuerying Publications only...")
    results = manager.query_submissions(
        query_text="research",
        n_results=5,
        content_type="Publication"
    )
    print(f"Publication results: {results}")

    # Query by department
    print("\nQuerying Computer Science department...")
    results = manager.query_submissions(
        query_text="technology",
        n_results=5,
        department="Computer Science"
    )
    print(f"Department results: {results}")
