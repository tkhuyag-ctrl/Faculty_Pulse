# RAG Improvements Needed for Faculty Pulse

## Current Problem

When asking for a detailed summary of the Tamoxifen paper (56K characters), the chatbot errors out or provides insufficient detail.

### Root Causes:

1. **Line 115 in chatbot.py truncates ALL documents to 500 characters**
   ```python
   formatted += f"Content: {doc[:500]}{'...' if len(doc) > 500 else ''}\n"
   ```
   - This defeats the purpose of having full PDF text (56K chars)
   - User asks for "detailed summary" but only gets 500 char snippet

2. **No intelligent text handling for large documents**
   - 56K character PDF treated same as 2K character abstract
   - No chunking strategy for long documents

3. **Context window limitations**
   - Claude 3 Haiku context window: 200K tokens (~150K characters)
   - If sending 10 results × 56K chars = 560K characters → **EXCEEDS LIMIT**
   - Current code tries to send all results without size management

4. **No RAG optimization**
   - No reranking of results
   - No chunk-level retrieval for large documents
   - No summary generation for context compression

---

## Solution 1: Adaptive Truncation (Quick Fix)

### Implementation:

Modify `format_database_results()` in [chatbot.py](chatbot.py:115):

```python
def format_database_results(self, results: Dict, max_total_chars: int = 100000) -> str:
    """
    Format database results with intelligent truncation

    Args:
        results: ChromaDB query results
        max_total_chars: Maximum total characters to include (default 100K)

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
        # Adaptive truncation based on relevance and remaining budget
        relevance = 1 - distance

        if relevance > 0.8 and total_chars < max_total_chars * 0.7:
            # High relevance: include more text (up to 20K chars)
            content_limit = min(20000, max_total_chars - total_chars - 1000)
        elif relevance > 0.5 and total_chars < max_total_chars * 0.9:
            # Medium relevance: include moderate text (up to 5K chars)
            content_limit = min(5000, max_total_chars - total_chars - 1000)
        else:
            # Low relevance: minimal text (500 chars)
            content_limit = 500

        content = doc[:content_limit]
        if len(doc) > content_limit:
            content += f"\n\n[Document truncated. Full length: {len(doc)} characters]"

        formatted += f"[Result {i} - Relevance: {relevance:.2f}]\n"
        formatted += f"Faculty: {metadata['faculty_name']}\n"
        formatted += f"Department: {metadata['department']}\n"
        formatted += f"Type: {metadata['content_type']}\n"
        formatted += f"Date: {metadata['date_published']}\n"
        formatted += f"Content: {content}\n"
        formatted += "-" * 80 + "\n\n"

        total_chars += len(content)

        # Stop if we're approaching the limit
        if total_chars > max_total_chars:
            formatted += f"\n[Additional results truncated to stay within context limits]\n"
            break

    return formatted
```

### Benefits:
- ✅ High-relevance results get more characters (up to 20K)
- ✅ Respects total context budget
- ✅ Quick to implement

### Limitations:
- ⚠️ Still might truncate important details
- ⚠️ No semantic chunking

---

## Solution 2: Document Chunking at Index Time (Medium Complexity)

### Strategy:

When adding documents to ChromaDB, split large PDFs into semantic chunks:

```python
def chunk_document(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """
    Split document into overlapping chunks

    Args:
        text: Full document text
        chunk_size: Target size per chunk
        overlap: Overlap between chunks

    Returns:
        List of text chunks
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence break (., !, ?)
            sentence_end = max(
                text.rfind('. ', start, end),
                text.rfind('! ', start, end),
                text.rfind('? ', start, end)
            )
            if sentence_end != -1:
                end = sentence_end + 2  # Include the punctuation

        chunks.append(text[start:end].strip())
        start = end - overlap  # Overlap for context

    return chunks
```

**Add chunks separately to ChromaDB**:

```python
def add_publication_with_chunking(pub, faculty_name, department, openalex_id, full_text):
    """Add publication with chunking for large documents"""

    if len(full_text) > 5000:  # Chunk large documents
        chunks = chunk_document(full_text, chunk_size=2000, overlap=200)

        for i, chunk in enumerate(chunks):
            chunk_content = f"""Faculty: {faculty_name}
Department: {department}
OpenAlex ID: {openalex_id}

Publication Title: {title}
Year: {year}

[Chunk {i+1}/{len(chunks)} of full paper]

{chunk}

This is part of a publication by {faculty_name} from {department}."""

            chroma.add_single_submission(
                document=chunk_content,
                faculty_name=faculty_name,
                date_published=pub_date,
                content_type='Publication',
                department=department,
                submission_id=f"pub_{openalex_id}_{work_id}_chunk_{i}"
            )
    else:
        # Add whole document for small papers
        chroma.add_single_submission(...)
```

### Benefits:
- ✅ Each chunk fits in context window
- ✅ Retrieval finds most relevant sections
- ✅ Can include multiple relevant chunks

### Limitations:
- ⚠️ Increases database size (56K doc → 28 chunks × 2K)
- ⚠️ Query might retrieve chunks from different papers
- ⚠️ Requires re-indexing existing data

---

## Solution 3: Two-Stage RAG (Best Approach)

### Stage 1: Retrieve Relevant Documents

```python
# First query: Find which documents are relevant
initial_results = query_database(query, n_results=10)

# Check top result relevance
top_relevance = 1 - initial_results['distances'][0][0]

if top_relevance > 0.7:  # High confidence match
    # Get the document ID
    doc_id = initial_results['ids'][0][0]
    full_doc = initial_results['documents'][0][0]
```

### Stage 2: Intelligent Context Generation

**For specific paper queries**:
```python
if "detailed summary" in query.lower() or "tell me about" in query.lower():
    # User wants detailed information
    # Strategy: Send full document or generate summary

    if len(full_doc) > 100000:  # Very large (like 56K)
        # Option A: Send full document (if fits)
        context = full_doc

        # Option B: Extract key sections using heuristics
        context = extract_key_sections(full_doc)

        # Option C: Generate summary first, then answer
        summary = generate_summary(full_doc)
        context = summary
```

**For general queries**:
```python
else:
    # User wants overview or multiple results
    # Use truncated versions
    context = format_database_results(results, max_chars_per_doc=1000)
```

### Implementation:

```python
def chat(self, user_query: str, n_results: int = 10) -> str:
    """Enhanced chat with intelligent context management"""

    # Query database
    results = self.query_database(user_query, n_results=n_results)

    if not results['ids'] or len(results['ids'][0]) == 0:
        return "I couldn't find any relevant information in the database."

    # Check if this is a specific paper query
    top_relevance = 1 - results['distances'][0][0]
    full_doc = results['documents'][0][0]

    # Detect query type
    is_detailed_query = any(keyword in user_query.lower() for keyword in [
        'detailed summary', 'tell me about', 'explain', 'describe in detail',
        'methodology', 'results', 'findings', 'what did', 'how did'
    ])

    if is_detailed_query and top_relevance > 0.7 and len(full_doc) > 10000:
        print(f"[DETAILED QUERY DETECTED]")
        print(f"Top result has {len(full_doc)} characters")
        print(f"Using full document context")

        # Send full document for detailed analysis
        database_context = self.format_full_document_result(results, index=0)
    else:
        print(f"[GENERAL QUERY]")
        print(f"Using truncated context from multiple results")

        # Use truncated multi-result format
        database_context = self.format_database_results(results, max_total_chars=50000)

    # Generate response
    response = self.generate_response(user_query, database_context)

    return response


def format_full_document_result(self, results: Dict, index: int = 0) -> str:
    """Format a single document with full content for detailed analysis"""

    doc = results['documents'][0][index]
    metadata = results['metadatas'][0][index]
    distance = results['distances'][0][index]
    relevance = 1 - distance

    formatted = f"""Here is the complete document from the faculty database:

[Relevance: {relevance:.2f}]
Faculty: {metadata['faculty_name']}
Department: {metadata['department']}
Type: {metadata['content_type']}
Date: {metadata['date_published']}

FULL DOCUMENT CONTENT:
{'='*80}

{doc}

{'='*80}

This is the complete content available for this publication."""

    return formatted
```

### Benefits:
- ✅ Adaptive to query type
- ✅ Sends full document when needed
- ✅ Falls back to summaries for general queries
- ✅ Respects context limits

### Limitations:
- ⚠️ Requires query intent detection
- ⚠️ Might still hit context limits with very large docs

---

## Solution 4: Hierarchical Summarization (Advanced)

### Strategy:

For very large documents (>50K chars):

1. **First pass**: Generate section summaries
   ```python
   sections = split_into_sections(full_doc)  # By headers, length, etc.
   summaries = [claude.summarize(section) for section in sections]
   ```

2. **Second pass**: Answer query using summaries + relevant sections
   ```python
   # Find most relevant sections
   relevant_sections = rank_sections_by_query(sections, user_query)

   # Combine summaries + full relevant sections
   context = "\n".join(summaries) + "\n\nDetailed sections:\n" + "\n".join(relevant_sections[:3])
   ```

3. **Third pass**: Generate final answer
   ```python
   response = claude.answer(user_query, context)
   ```

### Benefits:
- ✅ Handles arbitrarily large documents
- ✅ Provides both overview and detail
- ✅ Most sophisticated approach

### Limitations:
- ⚠️ Multiple API calls (expensive)
- ⚠️ Complex implementation
- ⚠️ Slower response time

---

## Recommended Implementation Plan

### Phase 1: Quick Fix (Immediate) ⭐

Implement **Solution 1: Adaptive Truncation**

1. Modify `format_database_results()` to:
   - Give high-relevance results more characters (20K)
   - Track total context size
   - Stop before exceeding limits

2. Add query type detection:
   - If query mentions specific paper → send more context
   - If general query → use truncated versions

**Effort**: 30 minutes
**Impact**: Solves immediate error, allows detailed queries

### Phase 2: Enhanced RAG (Short-term)

Implement **Solution 3: Two-Stage RAG**

1. Add query intent detection
2. Create `format_full_document_result()` method
3. Route queries to appropriate formatting

**Effort**: 2 hours
**Impact**: Much better user experience

### Phase 3: Document Chunking (Medium-term)

Implement **Solution 2: Chunking at Index Time**

1. Add chunking logic to PDF ingestion
2. Re-index Laura Been's publications
3. Update retrieval to handle chunks

**Effort**: 1 day
**Impact**: Scales to larger database

### Phase 4: Advanced RAG (Long-term)

Implement **Solution 4: Hierarchical Summarization**

1. Add section detection
2. Implement multi-stage summarization
3. Add section-level ranking

**Effort**: 3-5 days
**Impact**: Production-ready system

---

## Immediate Action: Fix the Error

The immediate error is likely due to:

1. **Context overflow**: Trying to send >200K tokens to Claude
2. **Truncation issue**: Truncating to 500 chars defeats the purpose

### Quick fix to stop the error:

```python
# In format_database_results(), line 115:

# OLD (causes issue):
formatted += f"Content: {doc[:500]}{'...' if len(doc) > 500 else ''}\n"

# NEW (adaptive):
content_limit = 20000 if (1-distance) > 0.8 else 2000 if (1-distance) > 0.5 else 500
content = doc[:content_limit]
formatted += f"Content: {content}{'...' if len(doc) > content_limit else ''}\n"
```

This will:
- Give top result (0.84 relevance) up to 20K characters
- Include meaningful portions of the full PDF
- Stop the error from context overflow

---

## Summary

**Yes, you need better RAG!**

Current issue:
- 500 char truncation defeats full PDF purpose
- No intelligent handling of large documents
- Context overflow when trying to send everything

Best solution:
1. **Immediate**: Adaptive truncation (Solution 1)
2. **Short-term**: Two-stage RAG (Solution 3)
3. **Long-term**: Document chunking (Solution 2)

The 56K PDF is valuable, but you need RAG strategies to use it effectively within Claude's context limits!
