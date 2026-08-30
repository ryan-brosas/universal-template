<!-- capsule-v2 -->
# Retry semantics — why does one scraper abort its whole batch on 429 while seven swallow errors?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How are retries, error swallowing, and fatal rate-limit signals divided between the infra layer, scrapers, and orchestrator?

## Three distinct regimes; RuntimeError IS the API contract
**Path/Symbol:** `stealth.py:retry_request` (:128-155, DEAD CODE); `instagram.py:scrape_profile_no_login` (:46-116); `scout.py:_standard_scrape_loop` except-ladder (:489-514).
**Signature:** scraper protocol: `(identifier: str) -> Dict | None`; raise `RuntimeError("Rate limited by ...")` as the ONLY fatal signal.

### Decisive source
```python
# scout.py — the orchestrator treats exception TYPES as control flow:
try:
    profile = scraper_func(item)
except RuntimeError as e:                    # rate limit ⇒ stop the WHOLE batch
    progress.stop()
    console.print(f"...rate limited...")
    break
except Exception as e:                       # anything else ⇒ skip this item
    progress.stop()
    console.print(f"...{str(e)[:80]}...")
# instagram.py raises it from BOTH detection sites:
if r.status_code == 429:
    raise RuntimeError("Rate limited by Instagram (429)...")
except Exception as e:
    err = str(e)
    if '429' in err:
        raise RuntimeError(...)              # proxy-layer 429s surface as text
```

**Flow:** generic scrapers (github/twitch/pinterest/linktree/youtube/tiktok/linkedin) convert every failure to `None` or log-and-return — one bad username never kills a bulk run. Only instagram escalates 429 to `RuntimeError`, and the shared loop is the single consumer that maps that type to `break`. The loop also silences library logging during each item (`setLevel(CRITICAL)` around the call unless `--verbose`) so third-party debug noise never interleaves with spinner output.
**Invariant:** `None` = this item failed but continue; `RuntimeError` = the platform is throttling YOU, stop everything (continuing would deepen the block). A porter who converts the RuntimeError into a returned None silently turns a protective abort into a hammering loop against a rate-limited endpoint. Note the string-sniffing `'429' in err` fallback exists because proxied requests can fail with the code buried in exception text.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -rn "RuntimeError" app/scrapers/` returns exactly instagram's two raise sites; `grep -n "except RuntimeError" scout.py` pins the sole consumer at :504. `retry_request` has zero call sites repo-wide (`grep -rn retry_request .`) — dead code, recorded as omit-with-reason, do not port as "the" retry mechanism.
**Coverage caveat:** pinned by source lines only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "RuntimeError rate limited scrape_profile_no_login", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed-signal contract (None=skip / specific Exception=fatal-batch) for any fan-out-over-unreliable-API loop; adapt which exception type carries the fatal signal to your host; omit `retry_request` (never wired) and keep the CRITICAL-level hush window only if you share Scout's spinner UX.
