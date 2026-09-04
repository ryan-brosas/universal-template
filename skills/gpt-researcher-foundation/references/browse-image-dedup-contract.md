<!-- capsule-v2 -->
# Browse side-effects & image dedup — what does a scrape pass register on the researcher, and how are duplicate images suppressed across passes?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Which researcher collections must a scrape pass update, and what is the exact image-selection predicate?

## BrowserManager.browse_urls + select_top_images
**Path/Symbol:** `gpt_researcher/skills/browser.py:37-84` (`browse_urls`), `:86-115` (`select_top_images`).
**Signature:** `async def browse_urls(self, urls: list[str]) -> list[dict]`; `def select_top_images(self, images: list[dict], k: int = 2) -> list[str]`.
**Data Shape:** scrape_urls returns `(scraped_content, images)` where images carry `{url, score}`; selection returns plain URL strings; dedup keys are `get_image_hash(img['url'])`.

### Decisive source
```python
# browser.py:55-60 — three side effects in fixed order:
scraped_content, images = await scrape_urls(
    urls, self.researcher.cfg, self.worker_pool
)
self.researcher.add_research_sources(scraped_content)
new_images = self.select_top_images(images, k=4)  # Select top 4 images
self.researcher.add_research_images(new_images)
...
# browser.py:101-113 — score-desc walk with TWO independent dedup guards:
for img in sorted(images, key=lambda im: im["score"], reverse=True):
    img_hash = get_image_hash(img['url'])
    if (img_hash and img_hash not in seen_hashes
            and img['url'] not in current_research_images):
        seen_hashes.add(img_hash)
        unique_images.append(img["url"])
        if len(unique_images) == k:
            break
```

**Flow:** every browse registers scraped pages into `research_sources` BEFORE compression sees them, then selects at most k=4 new images per call into `research_images` → because the worker pool is per-BrowserManager but the image collection lives on the shared researcher, nested deep-research children dedup against the PARENT's accumulated images via `current_research_images`.
**Invariant:** hash-unequal but byte-equal images (same content, different CDN URLs) collapse through the content hash; an unhashable/empty hash result (`img_hash` falsy) is skipped entirely. Signature default k=2 vs call-site k=4: the call site governs — porters copying the signature default silently halve image density. Selection happens even when zero pages scraped (empty input → empty selection, no error).
**Probe:** runner BLOCKED in-lane (missing aiofiles/deps; read-only checkout). Deterministic anchors verified byte-exact: `k=4)  # Select top 4 images` :59, `img['url'] not in current_research_images` :107, falsy-hash guard `if (\n                img_hash\n` :104-105. No upstream direct test exists for select_top_images (recorded caveat).
**Coverage:** check_index_coverage `no_recorded_issue`/`metadata_match` for skills/browser.py @ gen 2026-08-26T01:42:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "select_top_images get_image_hash add_research_images", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered side-effect triple and the two-guard image predicate; keep the researcher-owned cross-pass collection so child researchers inherit dedup state. Adapt scoring/hash to your extraction stack. Omit the hardcoded k values — make them config, but preserve call-site-wins semantics.
