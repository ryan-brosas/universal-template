<!-- capsule-v2 -->
# Feed post extraction via JS URN scan — how do I scrape a LinkedIn company/feed posts page by scanning the DOM for activity URNs instead of trusting card selectors?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`scrapers/company_posts.py` 346L). Codebase Memory `joeyism-linkedin-scraper`. **Question:** what is the URN-scan + text-block-selection strategy that survives LinkedIn's unstable feed card markup, and how does the scroll/limit loop stay bounded?

## URN-scan extraction + bounded scroll loop
**Path/Symbol:** `linkedin_scraper/scrapers/company_posts.py:CompanyPostsScraper._extract_posts_via_js` (:105–220), `_scrape_posts` (:82–100), `_wait_for_posts_to_load` (:44–65), `_trigger_lazy_load` (:67–80). **Signature:** `scrape(company_url, limit=10) -> List[Post]`; `_scrape_posts(limit)` loops `while len(posts) < limit and scroll_count < max_scrolls`.
**Data Shape:** each post is keyed by `urn:li:activity:<id>`; text is chosen from a selector ladder then a largest-text-block fallback; counts (reactions/comments/reposts) parsed via `re.findall(r'[\d,]+')`; images filtered to `img[src*="media"]` minus profile/logo.

### Decisive source
```js
// scan the whole body for activity URNs, then locate each post element by data-urn
const urnMatches = html.matchAll(/urn:li:activity:(\d+)/g);
const el = document.querySelector(`[data-urn="${urn}"]`);
// text: selector ladder, then largest non-nav text block fallback
const textSelectors = ['.feed-shared-update-v2__description', '.update-components-text',
  '.feed-shared-text', '[data-test-id="main-feed-activity-card__commentary"]', '.break-words.whitespace-pre-wrap'];
// fallback: largest div/span text >50 chars, skipping followers/reactions/nav/footer
```
```python
# bounded scroll loop: stop on limit OR max_scrolls
max_scrolls = (limit // 3) + 2
while len(posts) < limit and scroll_count < max_scrolls:
    new_posts = await self._extract_posts_from_page()
    for post in new_posts:
        if post.urn and not any(p.urn == post.urn for p in posts):
            posts.append(post)
    if len(posts) < limit:
        await self._scroll_for_more_posts(); scroll_count += 1
```

**Flow:** build `/posts/` URL → navigate → `check_rate_limit()` → wait for posts: poll `document.body.innerHTML.includes('urn:li:activity:')` across up to 3 lazy-load triggers (each a stepped `scrollTo` with 200ms intervals) → then the scroll loop: extract posts from the current DOM (URN-scan), dedupe by URN, scroll (`End` key) if under limit, bounded by `max_scrolls = limit//3 + 2` → return `posts[:limit]`.
**Invariant:** the URN is the identity — dedupe and post-URL construction both key on `urn:li:activity:<id>` (`https://www.linkedin.com/feed/update/urn:li:activity:<id>/`), so a post is never double-counted even when the same card appears across scrolls. Text selection must skip the actor/nav/footer blocks (reactions, "followers", `\d+[hdwmy]` time stamps) or you capture chrome instead of content. The loop is bounded by BOTH limit and max_scrolls so a page that never yields new posts still terminates.
**Probe:** `tests/test_company_scraper.py` exercises the flow behind the session fixture (integration-gated). Coverage: company_posts.py `no_recorded_issue`+`metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_extract_posts_via_js", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_scrape_posts", limit: 5 });
```

## Verdict
Adopt the URN-scan identity model, the selector-ladder-plus-largest-block text fallback, and the dual-bounded scroll loop; adapt the text selectors and count-parse regex (rot against live LinkedIn); omit the `Microsoft\n` hard-coded company filter (source-specific). Probe caveat: extraction is source-grounded, not test-pinned.
