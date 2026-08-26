<!-- capsule-v2 -->
# Retriever content cap — what stops one huge scraped page from blowing the embedding API's per-request limit?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Where is per-document content truncated before embedding, and why is the None coercion load-bearing?

## SearchAPIRetriever._get_relevant_documents
**Path/Symbol:** `gpt_researcher/context/retriever.py:9-38` (`_MAX_CONTENT_CHARS`, `SearchAPIRetriever`), `:40-70` (`SectionRetriever`).
**Signature:** `_MAX_CONTENT_CHARS = int(os.environ.get("MAX_CONTENT_CHARS", 50000))`
**Data Shape:** Input pages are scraper dicts (`{url, raw_content, title, image_urls}`); output is LangChain Documents with `{title, source}` metadata. Comment records the failure being prevented: scraped PDFs exceeding OpenAI's ~300k token-per-request cap.

### Decisive source
```python
docs = [
    Document(
        # ``raw_content`` may be explicitly None (the scraper sets it to
        # None for pages that failed to scrape), and slicing None raises
        # TypeError. Coerce to a string before truncating.
        page_content=(page.get("raw_content") or "")[:_MAX_CONTENT_CHARS],
        metadata={
            "title": page.get("title", ""),
            "source": page.get("url", ""),
        },
    )
    for page in self.pages
]
```

**Flow:** compressor pipeline invokes retriever first → every page truncated to 50k chars (~12.5k tokens) regardless of splitter → splitter then chunks within budget → EmbeddingsFilter drops irrelevant chunks.
**Invariant:** truncation happens at retrieval-entry, BEFORE any embedding call, and must tolerate `raw_content=None` (scraper contract: failed scrapes ARE in the list with None content — see `scraper.py` returning `{"raw_content": None, ...}`). SectionRetriever mirrors the shape for written sections but has NO cap (sections are already small).
**Probe:** battery P10d-e GREEN (`MAX_CONTENT_CHARS", 50000)` ×1; `(page.get("raw_content") or "")[:_MAX_CONTENT_CHARS]` ×1).
