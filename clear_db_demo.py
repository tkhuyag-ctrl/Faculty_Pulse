"""
Demonstration of clearing the ChromaDB database
"""
from chroma_manager import ChromaDBManager

if __name__ == "__main__":
    # Initialize the manager
    manager = ChromaDBManager()

    print("=" * 80)
    print("DATABASE CLEAR DEMONSTRATION")
    print("=" * 80)

    # Show current database state
    print("\n[STEP 1] Current database state:")
    count_before = manager.get_collection_count()
    print(f"Total submissions: {count_before}")

    if count_before > 0:
        manager.display_all_submissions()

    # Clear the database
    print("\n" + "-" * 80)
    print("[STEP 2] Clearing database...")
    manager.clear_database()

    # Verify it's empty
    print("\n" + "-" * 80)
    print("[STEP 3] Verifying database is empty:")
    count_after = manager.get_collection_count()
    print(f"Total submissions: {count_after}")

    if count_after == 0:
        print("✓ Database successfully cleared!")
    else:
        print("✗ Something went wrong - database not empty")

    print("\n" + "=" * 80)
