"""
Clear the ChromaDB database
"""
import sys
from chroma_manager import ChromaDBManager

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def clear_database():
    """Clear all data from the database"""
    print("\n" + "="*80)
    print("DATABASE CLEARING UTILITY")
    print("="*80 + "\n")

    manager = ChromaDBManager(persist_directory="./chroma_db")

    # Get current count
    current_count = manager.get_collection_count()
    print(f"Current documents in database: {current_count}")

    if current_count == 0:
        print("\n✓ Database is already empty. Nothing to clear.")
        return

    # Confirm and clear
    print(f"\n⚠️  WARNING: This will permanently delete all {current_count} documents!")
    print("Clearing database...")

    manager.clear_database()

    # Verify
    new_count = manager.get_collection_count()
    print(f"\n✓ Database cleared successfully!")
    print(f"Documents remaining: {new_count}")

    if new_count == 0:
        print("\n✓ Database is now empty and ready for new data.")
    else:
        print(f"\n⚠️  Warning: {new_count} documents still remain in the database.")


if __name__ == "__main__":
    clear_database()
