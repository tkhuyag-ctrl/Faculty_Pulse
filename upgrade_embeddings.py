"""
Upgrade ChromaDB to use a better embedding model
This will create a NEW collection with better embeddings and migrate all data
"""
import chromadb
from chromadb.utils import embedding_functions
import logging
from datetime import datetime
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade_to_better_embeddings():
    """Migrate to all-mpnet-base-v2 (much better quality than default)"""

    print("="*80)
    print("CHROMADB EMBEDDING MODEL UPGRADE")
    print("="*80)
    print("\nCurrent model: all-MiniLM-L6-v2 (22M params, dim 384)")
    print("New model:     all-mpnet-base-v2 (110M params, dim 768)")
    print("\nThis will:")
    print("  1. Create a new collection with better embedding model")
    print("  2. Copy all 2322 documents to new collection")
    print("  3. Rename old collection to 'faculty_pulse_old'")
    print("  4. Rename new collection to 'faculty_pulse'")
    print("\nEstimated time: 5-10 minutes")
    print("="*80)

    response = input("\nProceed? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Initialize client
    client = chromadb.PersistentClient(path="./chroma_db")

    # Get old collection
    print("\n[1/5] Loading existing collection...")
    old_collection = client.get_collection(name="faculty_pulse")
    total_docs = old_collection.count()
    print(f"      Found {total_docs} documents")

    # Create better embedding function
    print("\n[2/5] Initializing better embedding model (all-mpnet-base-v2)...")
    print("      This will download ~420MB model on first run...")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="sentence-transformers/all-mpnet-base-v2"
    )
    print("      Model loaded!")

    # Create new collection with better embeddings
    print("\n[3/5] Creating new collection with upgraded embeddings...")
    try:
        client.delete_collection(name="faculty_pulse_new")
    except:
        pass

    new_collection = client.create_collection(
        name="faculty_pulse_new",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    print("      New collection created!")

    # Migrate data in batches
    print(f"\n[4/5] Migrating {total_docs} documents...")
    batch_size = 100
    migrated = 0

    # Get all data
    all_data = old_collection.get(include=['documents', 'metadatas', 'embeddings'])

    # Process in batches
    for i in tqdm(range(0, len(all_data['ids']), batch_size), desc="Migrating"):
        batch_end = min(i + batch_size, len(all_data['ids']))

        batch_ids = all_data['ids'][i:batch_end]
        batch_docs = all_data['documents'][i:batch_end]
        batch_metas = all_data['metadatas'][i:batch_end]

        # Add to new collection (will re-embed with new model)
        new_collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas
        )

        migrated += len(batch_ids)

    print(f"\n      Successfully migrated {migrated} documents!")

    # Verify counts match
    new_count = new_collection.count()
    assert new_count == total_docs, f"Count mismatch! Old: {total_docs}, New: {new_count}"

    # Rename collections
    print("\n[5/5] Swapping collections...")
    print("      Renaming 'faculty_pulse' -> 'faculty_pulse_old' (backup)")
    try:
        client.delete_collection(name="faculty_pulse_old")
    except:
        pass

    # Note: ChromaDB doesn't have direct rename, so we need to:
    # 1. Create backup by copying old to "faculty_pulse_old"
    # 2. Delete old "faculty_pulse"
    # 3. Create new "faculty_pulse" with new embedding function
    # 4. Copy data from "faculty_pulse_new"

    # Create backup
    backup_collection = client.create_collection(
        name="faculty_pulse_old",
        metadata={"hnsw:space": "cosine"}
    )
    for i in range(0, len(all_data['ids']), batch_size):
        batch_end = min(i + batch_size, len(all_data['ids']))
        backup_collection.add(
            ids=all_data['ids'][i:batch_end],
            documents=all_data['documents'][i:batch_end],
            metadatas=all_data['metadatas'][i:batch_end]
        )

    # Delete old collection
    client.delete_collection(name="faculty_pulse")

    # Create new main collection with better embeddings
    main_collection = client.create_collection(
        name="faculty_pulse",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

    # Copy from new to main
    new_data = new_collection.get(include=['documents', 'metadatas'])
    for i in range(0, len(new_data['ids']), batch_size):
        batch_end = min(i + batch_size, len(new_data['ids']))
        main_collection.add(
            ids=new_data['ids'][i:batch_end],
            documents=new_data['documents'][i:batch_end],
            metadatas=new_data['metadatas'][i:batch_end]
        )

    # Delete temp collection
    client.delete_collection(name="faculty_pulse_new")

    print("\n" + "="*80)
    print("UPGRADE COMPLETE!")
    print("="*80)
    print(f"Main collection 'faculty_pulse' now uses all-mpnet-base-v2")
    print(f"Backup saved as 'faculty_pulse_old' (can be deleted later)")
    print(f"Total documents: {main_collection.count()}")
    print("\nSearch quality should be MUCH better now!")
    print("\nRestart your Streamlit app to use the upgraded collection.")


if __name__ == "__main__":
    upgrade_to_better_embeddings()
