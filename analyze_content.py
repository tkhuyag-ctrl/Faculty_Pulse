"""
Analyze full text vs abstract content in database
"""
import sys
from chroma_manager import ChromaDBManager

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("\n" + "="*80)
    print("DATABASE CONTENT ANALYSIS")
    print("="*80 + "\n")

    manager = ChromaDBManager()
    results = manager.collection.get(include=['documents', 'metadatas'])
    docs = results['documents']

    # Analyze content types
    full_pdf = 0
    abstract_only = 0

    for doc in docs:
        if 'FULL PAPER TEXT:' in doc:
            full_pdf += 1
        elif 'Abstract:' in doc and len(doc) < 10000:
            abstract_only += 1
        elif len(doc) > 20000:  # Large docs are likely full PDFs even without marker
            full_pdf += 1
        else:
            abstract_only += 1

    print(f"Total Documents: {len(docs)}")
    print(f"\nContent Types:")
    print(f"  Full PDF Text: {full_pdf} ({full_pdf/len(docs)*100:.1f}%)")
    print(f"  Abstract Only: {abstract_only} ({abstract_only/len(docs)*100:.1f}%)")

    # Calculate average lengths
    all_lengths = [len(d) for d in docs]
    full_pdf_lengths = [len(d) for d in docs if len(d) > 20000 or 'FULL PAPER TEXT:' in d]
    abstract_lengths = [len(d) for d in docs if len(d) <= 20000 and 'FULL PAPER TEXT:' not in d]

    print(f"\nAverage Document Length:")
    print(f"  Overall: {sum(all_lengths)/len(all_lengths):,.0f} characters")
    if full_pdf_lengths:
        print(f"  Full PDFs: {sum(full_pdf_lengths)/len(full_pdf_lengths):,.0f} characters")
    if abstract_lengths:
        print(f"  Abstracts: {sum(abstract_lengths)/len(abstract_lengths):,.0f} characters")

    # Show document length distribution
    print(f"\nDocument Length Distribution:")
    ranges = [
        (0, 2000, "Very Short (0-2K)"),
        (2000, 5000, "Short (2-5K)"),
        (5000, 20000, "Medium (5-20K)"),
        (20000, 50000, "Large (20-50K)"),
        (50000, 100000, "Very Large (50-100K)"),
        (100000, float('inf'), "Huge (100K+)")
    ]

    for min_len, max_len, label in ranges:
        count = sum(1 for d in docs if min_len <= len(d) < max_len)
        if count > 0:
            print(f"  {label}: {count} ({count/len(docs)*100:.1f}%)")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
