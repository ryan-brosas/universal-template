<!-- capsule-v2 -->
# Scraper routing + dedupe — which backend handles which URL, and what happens to duplicates and short pages?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** What is the URL→scraper dispatch order, and which two guards keep scraping cheap and honest?

## Scraper.get_scraper dispatch table
**Path/Symbol:** `gpt_researcher/scraper/scraper.py:172-217` (`get_scraper`), `:42-46` (dedupe), `:109-170` (`extract_data_from_url`), session close in `actions/web_scraping.py:42-46`.
**Signature:** `def get_scraper(self, link) -> type` over `SCRAPER_CLASSES = {pdf, arxiv, bs, web_base_loader, browser, nodriver, tavily_extract, firecrawl}`.
**Data Shape:** Success dict `{url, raw_content, image_urls, title}`; failures/short pages carry `raw_content: None` and are filtered by `run()`.

### Decisive source
```python
path = urlparse(link).path
if path.lower().endswith(".pdf"):
    scraper_key = "pdf"        # query-string-safe: signed CDN links like .../doc.pdf?sig=…
elif "arxiv.org" in link:
    scraper_key = "arxiv"
else:
    scraper_key = self.scraper  # configured backend
...
unique_urls = list(dict.fromkeys(urls))  # Preserves order while removing duplicates
```

**Flow:** constructor dedupes preserving order → `asyncio.gather` over URLs each throttled by the WorkerPool → sync scrapers run via executor, async ones via `scrape_async()` → content <100 chars nulled (guard appears TWICE — :134 and :152 dead twin; harmless but a porter should keep one) → `finally: scraper.session.close()` releases the connection pool.
**Invariant:** PDF sniff inspects ONLY the path component case-insensitively (a `.pdf` substring in query params must NOT route to PyMuPDF); arXiv beats configured backend; unknown scraper key raises "Scraper not found." tavily_extract/firecrawl trigger auto-pip-install of their packages at init.
**Probe:** `tests/test_scraper_get_scraper.py` pins pdf/query/fragment/uppercase/query-substring routing; battery P07a-d GREEN (`len\(content\) < 100` ×2 proves the dead twin).
