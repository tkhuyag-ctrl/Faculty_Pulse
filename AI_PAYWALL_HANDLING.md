# How the AI Handles Paywalled and Inaccessible Papers

## Overview

After the PDF extraction completes, your Faculty Pulse chatbot will intelligently handle three types of publication access:

1. **Full Text Available** - AI can read and summarize the complete paper
2. **Behind Paywall** - AI acknowledges limitations and provides metadata
3. **Not Found** - AI explains unavailability and provides what's known

---

## Example Conversations

### Scenario 1: Full Text Available ✓

**User:** "Summarize Laura Been's 2022 paper on postpartum depression"

**AI Response:**
> Based on Laura Been's 2022 publication "Postpartum estrogen withdrawal induces deficits in affective behaviors":
>
> **Summary:** This study investigated how rapid estrogen withdrawal after pregnancy contributes to postpartum depression. The researchers used a hormone-simulated pregnancy model in rats and found that:
>
> 1. **Key Finding:** Estrogen withdrawal following simulated pregnancy induced depressive-like behaviors, including increased immobility in forced swim tests and reduced sucrose preference
>
> 2. **Mechanism:** The study identified changes in the posterior bed nucleus of the stria terminalis (pBNST) as a potential neural mechanism
>
> 3. **Implications:** These findings suggest that hormonal changes, specifically estrogen withdrawal, play a direct causal role in postpartum mood disorders
>
> The paper was published in [Journal Name], has 8 citations, and is available as open access.
>
> **Full text extracted:** 15,578 words analyzed

---

### Scenario 2: Behind Paywall ⚠

**User:** "What does the paper about quantum computing by Physics faculty say?"

**AI Response:**
> I found a publication on quantum computing, but unfortunately **this paper is behind a paywall** and I don't have access to the full text.
>
> Here's what I can tell you from the metadata:
>
> **Publication Details:**
> - **Title:** "Quantum Error Correction in Topological Systems"
> - **Author:** Bruce Partridge (Physics Department)
> - **Year:** 2023
> - **Published in:** Nature Physics
> - **Citations:** 42
> - **Status:** Behind paywall - requires institutional access or purchase
>
> **To access the full paper:**
> - DOI: https://doi.org/10.1038/nphys.xxxx
> - You may be able to access it through Haverford's library system
> - Check if your institution has a subscription to Nature Physics
>
> I can only provide the publication metadata, not the research content, methodology, or findings. Would you like me to search for other open access papers by this faculty member?

---

### Scenario 3: Not Found in Open Access ✗

**User:** "Tell me about Robert Fairman's research on protein folding"

**AI Response:**
> I found a publication on protein folding by Robert Fairman (Biology Department), but **the full text is not available in open access repositories**.
>
> **Publication Details:**
> - **Title:** "Chaperone-Mediated Protein Folding in Cellular Stress"
> - **Year:** 2021
> - **Published in:** Journal of Biological Chemistry
> - **Citations:** 15
> - **Open Access:** No
> - **Status:** Full text not found in open access repositories
>
> **Why it's unavailable:**
> This paper is likely behind a paywall or not digitally indexed in the open repositories I searched (Unpaywall, OpenAlex, arXiv).
>
> **How to access:**
> - Visit the publisher's website via the DOI: [DOI link]
> - Check Haverford's library for institutional access
> - Contact the author directly for a preprint copy
>
> I can only provide metadata about this publication, not its content. Would you like to know about other publications by this faculty member that might have open access?

---

## How the AI Determines Access Status

### During Database Population:

```python
# The script tries to:
1. Find PDF URL from Unpaywall (open access aggregator)
2. Find PDF URL from OpenAlex (direct links)
3. Search arXiv (preprint repository)
4. Download the PDF if found
5. Extract text using pypdf library

# Then categorizes as:
- "full_text" → PDF found + text extracted successfully
- "paywall" → PDF URL found but extraction failed (likely paywalled/broken)
- "not_found" → No PDF found in any open repository
```

### Stored in Database:

Each publication document includes explicit access information:

```
Publication Title: [Title]
Year: 2023
Access Status: BEHIND PAYWALL - Full text not accessible
Publisher URL: https://...
Note: This publication requires institutional access or purchase.

FULL TEXT UNAVAILABLE - BEHIND PAYWALL

This paper is published in a subscription journal and requires institutional
access or purchase. Only metadata is available for searching and reference.

To access the full paper, visit: [DOI]
```

---

## AI Behavior by Access Type

### Full Text Available (access_status = "full_text")

**The AI will:**
- ✓ Read the entire paper content
- ✓ Summarize research findings
- ✓ Answer detailed methodology questions
- ✓ Quote specific sections
- ✓ Compare findings across papers
- ✓ Explain technical concepts from the paper
- ✓ Identify key contributions

**Example queries it can handle:**
- "What statistical methods were used?"
- "What were the limitations mentioned?"
- "How large was the sample size?"
- "What did the discussion section conclude?"

---

### Behind Paywall (access_status = "paywall")

**The AI will:**
- ⚠ Acknowledge it's behind a paywall upfront
- ⚠ Provide all available metadata (title, author, year, citations, journal)
- ⚠ Explain why full text isn't accessible
- ⚠ Provide DOI/publisher links for access
- ⚠ Suggest alternative access methods
- ⚠ Offer to find other open access papers by the same faculty

**The AI will NOT:**
- ✗ Guess or speculate about the paper's content
- ✗ Make up findings or methodology
- ✗ Pretend to have read it
- ✗ Provide a summary without access

**Example response:**
> "I see this paper has 42 citations and was published in Nature Physics in 2023, but I cannot access the full text as it's behind a paywall. I can tell you about the publication metadata, or I can search for other open access papers on similar topics by this faculty member."

---

### Not Found (access_status = "not_found")

**The AI will:**
- ✗ Explain the paper wasn't found in open access repositories
- ✗ Provide metadata (title, author, year, citations)
- ✗ Suggest why it might be unavailable (not open access, not in indexed repos)
- ✗ Recommend ways to access (library, author contact, DOI)
- ✗ Offer alternatives (other papers by faculty, related topics)

**The AI will NOT:**
- ✗ Fabricate content
- ✗ Assume anything about the research
- ✗ Provide false hope about access

---

## Transparency is Key

The AI is programmed to be **completely transparent** about access limitations:

### Good AI Response (Honest):
> "I don't have access to the full text of this paper because it's behind a paywall. From the metadata, I can see it's about X and was published in Y journal with Z citations. For the actual findings and methodology, you would need to access the paper through [methods]."

### Bad AI Response (Would Never Happen):
> ~~"Based on this paper [makes up findings without having read it]..."~~

---

## Statistics You'll See

After extraction completes, you'll see something like:

```
================================================================================
PDF EXTRACTION SUMMARY
================================================================================
Total publications: 228

Access Status Breakdown:
  [OK] Full text extracted: 68 (29.8%)
  [PAYWALL] Behind paywall: 32 (14.0%)
  [NOT FOUND] Not found: 128 (56.2%)
================================================================================
```

**This is normal!** Academic publishing has significant paywall barriers:
- Many prestigious journals are subscription-only
- Not all faculty publish in open access venues
- Some papers predate open access movements
- Certain fields have lower OA rates than others

---

## Benefits of This Approach

### 1. **Honesty**
Users always know what the AI can and cannot access

### 2. **Useful Even Without Full Text**
Metadata alone is valuable:
- Citation counts indicate impact
- Publication years show research timeline
- Journal names indicate prestige/field
- DOIs enable proper citations

### 3. **Clear Next Steps**
AI always tells users how to access paywalled papers:
- Library systems
- Publisher websites
- Author contact
- Institutional repositories

### 4. **No Hallucinations**
AI never fabricates research findings it hasn't read

---

## Example Multi-Paper Query

**User:** "Compare the research methods of the three most cited Biology papers"

**AI Response:**
> I found the three most cited Biology publications from 2020-2025:
>
> **1. [Paper 1 - 89 citations] - FULL TEXT AVAILABLE**
> This paper used quantitative PCR and Western blotting to analyze protein expression. The study included 45 subjects and employed a randomized controlled design...
>
> **2. [Paper 2 - 67 citations] - BEHIND PAYWALL**
> I don't have access to the full methodology for this paper, but the metadata shows it was published in Cell Biology Journal. For detailed methods, you would need to access the paper at [DOI].
>
> **3. [Paper 3 - 54 citations] - FULL TEXT AVAILABLE**
> This paper used CRISPR-Cas9 gene editing combined with fluorescence microscopy. The experimental design included both in vitro and in vivo models...
>
> For paper #2, I can only provide what's in the title and metadata since it's paywalled. Would you like me to search for an open access version or look for related papers I can fully access?

---

## User Questions the AI Can Answer

### About Access:
- "Which papers by [faculty] can you fully access?"
- "Are there any open access papers about [topic]?"
- "Why can't you read this specific paper?"

### About Paywalled Papers:
- "How can I access this paywalled paper?"
- "Where was this paper published?"
- "How many times has this paper been cited?"

### About Available Papers:
- "Summarize [paper title]"
- "What methods were used in [paper]?"
- "What were the main findings?"
- "Compare these two papers"

---

## Technical Implementation

### In chroma_manager.py / chatbot.py

The AI system prompt will include:

```python
system_prompt = """
When answering questions about research papers:

1. Check the access_status field in metadata
2. If "full_text": Provide detailed answers based on paper content
3. If "paywall": Acknowledge paywall, provide metadata only, suggest access methods
4. If "not_found": Explain unavailability, provide metadata, suggest alternatives

NEVER fabricate research findings you haven't read.
ALWAYS be transparent about access limitations.
ALWAYS provide actionable next steps for accessing paywalled content.
"""
```

### Metadata Fields Used:

```json
{
  "access_status": "full_text" | "paywall" | "not_found",
  "has_full_text": true | false,
  "pdf_url": "https://..." | "",
  "doi": "https://doi.org/...",
  "publication_title": "...",
  "cited_by_count": 42,
  "is_open_access": true | false
}
```

---

## Summary

Your Faculty Pulse AI will handle research papers intelligently:

| Access Type | AI Can Do | AI Cannot Do |
|-------------|-----------|--------------|
| **Full Text** | Read, summarize, analyze, compare | Nothing - full access |
| **Paywall** | Provide metadata, guide to access | Make up content, guess findings |
| **Not Found** | Explain status, suggest alternatives | Pretend to have read it |

**Key Principle:** The AI is always honest about what it can and cannot access, making it a reliable research assistant that users can trust.

---

**Current Status:** PDF extraction in progress
**When Complete:** All 228 publications will be properly categorized
**Result:** Transparent, honest, and helpful research assistance
