<!-- capsule-v2 -->
# Profile contract — what fields must every platform scraper return, and why is follower_count load-bearing?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What is the cross-platform data contract that lets one loop, one enricher, and one CSV writer serve eight platforms?

## Duck-typed dict protocol with platform-specific extras
**Path/Symbol:** all eight builders — e.g. `app/scrapers/instagram.py:_extract_profile_from_html` return (:246-261), `github.py:scrape_profile` (:62-77), `linkedin.py` (:142-154); consumers `scout.py:_standard_scrape_loop/_standard_export/enrich_profiles`.
**Signature:** `scraper(identifier: str) -> Optional[Dict[str, Any]]`; `None` on not-found/empty.
**Data Shape:** common core: `username, full_name, bio, email, follower_count, website, platform, profile_url`. Per-platform extras ride along untouched (instagram: `is_verified/is_private/is_business/post_count/following_count/phone`; github: `company/location/twitter/public_repos/is_hireable`; youtube: `links[]/channel_id/subscriber_count-as-follower_count`; twitch: `is_partner/is_affiliate/links[]`; linktree family: `links[]/socials{}/link_count`; tiktok: `likes_count/video_count`; pinterest: `pin_count/board_count/verified`; linkedin: `headline/is_premium/is_influencer/company_domain-later`).

### Decisive source
```python
# instagram.py — the validity gate that everything downstream trusts:
if 'follower_count' not in results or results.get('follower_count', 0) == 0:
    return None                       # a real profile always has ≥1 follower

# github.py — empty-profile skip keeps junk out of lead exports:
if not any([data.get('name'), data.get('bio'), data.get('email'),
            data.get('blog'), data.get('company'), data.get('twitter_username')]):
    return None
```

**Flow:** orchestrator counts success as `profile` truthiness, prints cards by `.get()`, hands the list to `enrich_profiles` (which reads `full_name/bio/website/company/headline` when present), then writes CSV with `fieldnames=profiles[0].keys()` — first row's keys become the header, so missing-first-row fields silently vanish from the export.
**Invariant:** `follower_count > 0` doubles as the instagram authenticity gate (login-wall pages parse to zero); `platform` must be set literally per scraper because it keys enrichment behavior and filenames; enrichment ADDS keys (`email_score/email_source/email_verified/lead_score/possible_emails/company_domain`) rather than replacing the dict, so CSV schemas grow monotonically. The linktree interactive path is the exception that proves the rule — it pre-flattens `links/socials` into `social_<platform>` columns precisely BECAUSE nested values would break the flat CSV writer.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "'platform':" app/scrapers/*.py` pins NINE string-literal assignments (github/instagram/linkedin/pinterest/tiktok/twitch/youtube + linktree's structured parsers :150 `'linktree'` /:186 `'stan'`) PLUS the generic parser's variable form `'platform': platform` at :226; `grep -n "fieldnames=profiles\[0\]" scout.py` pins :532/:863.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "platform follower_count profile_url", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the duck-typed add-only profile protocol with a truthiness validity gate; adapt field names freely but keep `platform` + monotonic key growth if you reuse the enricher or flat CSV path; omit the first-row-schema fragility by deriving the union of keys (as the linktree branch already does) when porting.
