<!-- capsule-v2 -->
# Compose-then-self-reply — how do you post an image+text tweet that dodges link throttling, and recover the URL?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When posting to X.com, why does the link go in a self-reply instead of the main tweet, and how is the tweet composed to fit 280 chars and its URL recovered without an API?

## Content pipeline: 280-fit compose ladder + timeline-scrape URL + self-reply with link
**Path/Symbol:** `workflows/executors/hf-papers-to-x.ts`: `composeTweet` (:342-360), `getPostUrl` (:367-385), `replyWithLink` (:390-432), `postOnePaper` (:434-501), `findRef` (:140-144), `abEval` (:120-138).
**Signature:** `composeTweet(paper): string`; `getPostUrl(): string | null`; `replyWithLink(tweetUrl, paperLink): boolean`; `postOnePaper(paper): 'success' | 'failed'`.
**Data Shape:** Main tweet = `title + abstract + "N upvotes on HuggingFace Daily Papers"` with NO links/hashtags; abstract truncated to fit; URL harvested from `a[href*="/<username>/status/"]` sorted by BigInt snowflake ID.

### Decisive source
```ts
function composeTweet(paper: Paper): string {
  let tweet = `${paper.title}\n\n${paper.abstract}\n\n${paper.upvotes} upvotes on HuggingFace Daily Papers`
  if (tweet.length > 280) {
    const target = 280 - (paper.title.length + 50)   // 50 = upvotes line + newlines
    const shortAbstract = paper.abstract.slice(0, Math.max(target, 20)) + '...'
    tweet = `${paper.title}\n\n${shortAbstract}\n\n${paper.upvotes} upvotes on HuggingFace Daily Papers`
  }
  if (tweet.length > 280) tweet = `${paper.title}\n\n${paper.upvotes} upvotes on HuggingFace Daily Papers`  // drop abstract
  return tweet
}
// getPostUrl: filter a[href*="/<user>/status/"], then sort by BigInt status ID
// (never parseInt — snowflake IDs exceed 2^53), return highest (most recent).
```

**Flow:** compose tweet fitting 280 (shorten abstract → drop abstract) → open X.com home → `upload 'input[type="file"]'` the thumbnail → `fill` the `textbox "Post text"` → click `Post` with retry ladder (verify by absence of title in `[role="textbox"]`) → `getPostUrl` from timeline (BigInt-sorted most-recent status link) → `replyWithLink` navigates to the tweet, fills `Paper: <link>` in the reply textbox, clicks `Reply` (retry ≤3, verify textbox no longer contains `Paper:`) → return `success` even if reply fails (main tweet already posted).
**Invariant:** Links/hashtags NEVER go in the main tweet — they go in the self-reply, because X.com throttles link-bearing posts. The compose ladder guarantees a valid ≤280 tweet by degrading gracefully (shorten abstract, then drop it) rather than failing. Tweet URL recovery is a pure DOM scrape sorted by BigInt snowflake ID — `parseInt` on status IDs loses precision past 2^53. The reply's success is verified by the compose textbox no longer containing the reply text, and a failed self-reply must NOT fail the main post (degrade-don't-fail).
**Probe:** No direct test exists for this executor (coverage caveat — source-grounded). Deterministic probes: grep-pinned comment :344 (links-in-self-reply rationale), :349 (280-fit target math), :373-377 (BigInt sort); `search_graph` resolves `composeTweet` :342-360 / `getPostUrl` :367-385 / `replyWithLink` :390-432 / `postOnePaper` :434-501 line-exact; `trace_path` `postOnePaper` → 14 callees incl. `composeTweet`/`getPostUrl`/`replyWithLink`/`findRef`/`switchToX`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "composeTweet getPostUrl replyWithLink self-reply BigInt status", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the 280-fit compose ladder, link-in-self-reply to dodge throttling, BigInt-snowflake timeline-scrape URL recovery (never parseInt), and degrade-don't-fail reply handling. Adapt the username, thumbnail source, compose selectors, and retry counts. Omit nothing in the compose ladder — dropping the graceful-degrade steps makes a long abstract fail the whole post. Coverage caveat: no direct test; behavior source-grounded.
