<!-- capsule-v2 -->
# Snowflake-ID post-URL capture with BigInt ordering — how do you identify the tweet you just posted when the timeline offers many status links?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** After a successful post, how is the new tweet's URL extracted from the home timeline without an API handle — and why must sorting never use `parseInt`?

## Username-scoped link harvest + BigInt-descending pick
**Path/Symbol:** `workflows/executors/hf-papers-to-x.ts`:`getPostUrl` (`:367-385`); identical logic in `post-hf-paper.ts:190-207` (single-op variant). Consumed by `replyWithLink` (`hf-papers-to-x.ts:390-432`).
**Signature:** `getPostUrl(): string | null` — eval'd JS returns `JSON.stringify(urls[0] || null)`; wrapper unwraps quoted strings and treats `'null'`/missing `/status/` as failure.
**Data Shape:** Input DOM: anchors `a[href*="/<username>/status/"]`. Filter regex: `\/<username>\/status\/\d+$`. Sort key: `BigInt(id)` where id = segment after `/status/`. Output: one canonical URL or null (caller degrades to post-without-reply, still 'success').

### Decisive source
```ts
const links = document.querySelectorAll(`a[href*="/${xUsername}/status/"]`);
const urls = Array.from(links).map(a => a.href)
  .filter(h => h.match(new RegExp(`\\/${xUsername}\\/status\\/\\d+$`)));
// Return the one with highest status ID (most recent)
urls.sort((a, b) => {
  const idA = BigInt(a.split('/status/')[1] || '0');
  const idB = BigInt(b.split('/status/')[1] || '0');
  return idB > idA ? 1 : idB < idA ? -1 : 0;
});
JSON.stringify(urls[0] || null);
```

**Flow:** wait ~2 s after the Post click → in the X tab's timeline, collect every anchor whose href contains `/<own username>/status/` → keep only links ENDING in a numeric status id → sort DESCENDING by the id interpreted as BigInt → take the max (snowflake ids are time-ordered ⇒ newest wins) → return it for the self-reply step. If extraction fails, the executor logs "posted but reply skipped" and grades the paper SUCCESS — the irreversible action landed; only the optional link-reply was lost.
**Invariant:** Status IDs exceed 2^53 — `parseInt` silently corrupts adjacent-id comparisons (classic wrong port), so the comparator MUST be string/BigInt-based. The username scope (`href*="/me/status/"`) excludes other people's tweets from the candidate set. Failure of this read-only enrichment step must NOT fail the whole operation: the dedup-worthy event (the post) already happened. The same extract-then-degrade contract appears verbatim in both executors.
**Probe:** No upstream executor tests (browser pipelines). Deterministic source-grounded probes: BigInt comparator at `hf-papers-to-x.ts:373-377` and mirrored at `post-hf-paper.ts:194-198`, null-tolerant unwrap at `hf-papers-to-x.ts:381-384` and `post-hf-paper.ts:203-207`. Coverage caveat recorded; port with a unit test pinning e.g. `'1234567890123456789' > '1234567890123456788'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getPostUrl replyWithLink snowflake BigInt", limit: 10 });
```
Graph resolves `getPostUrl` :367-385 and `replyWithLink` :390-432 line-exact.

## Verdict
Adopt username-scoped harvesting, strict-suffix numeric filtering, BigInt descending selection, and degrade-don't-fail on extraction miss. Adapt the selector/regex to your platform's URL grammar (any time-ordered ID domain benefits — not just snowflakes). Omit API-based lookup — the whole point is zero-API posting from the logged-in browser session.
