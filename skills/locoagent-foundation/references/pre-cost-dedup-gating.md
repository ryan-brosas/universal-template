<!-- capsule-v2 -->
# Pre-cost dedup gating — how do you skip already-done targets before paying for navigation, reads, or LLM calls?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Where in a repeatable browser workflow should the "did I already do this?" check run so repeats cost nothing and a fully-done day still reports success?

## Load the matching source dump
**Path/Symbol:** `workflows/executors/x-search-reply.ts`: replied-store load + Set (`:102-103`), per-target flag (`:311-317`), zero-work exit (`:323-331`). Same convention: `workflows/executors/linkedin-search-reply.ts:369-373`.
**Signature:** `const repliedUrls = new Set(repliedStore.posts.map(p => p.postUrl))`; `PostInfo.skippedDedup: boolean`; `newPosts = posts.filter(p => !p.skippedDedup)`.
**Data Shape:** Dedup entries `{ postUrl, repliedAt, searchQuery }`; each harvested target carries its own `skippedDedup` flag computed at harvest time.

### Decisive source
```ts
posts = postUrls.map(url => ({ url, content: '', replyText: '', replied: false,
  skippedDedup: repliedUrls.has(url) }))            // gate computed BEFORE any work
const newPosts = posts.filter(p => !p.skippedDedup)
// ...
if (newPosts.length === 0) {
  log('No new posts to reply to.')
  steps.push({ step: 'read_posts',      status: 'skipped' })
  steps.push({ step: 'generate_replies', status: 'skipped' })
  steps.push({ step: 'post_replies',    status: 'skipped' })
  skippedCount = posts.length
  outputResult(); process.exit(0)                   // SUCCESS exit, full envelope
}
```

**Flow:** load the persisted dedup store once at boot → build an in-memory Set of done keys → mark EVERY harvested target with its `skippedDedup` flag before any browser action → read/generate loops iterate `newPosts` only → if nothing is new, emit explicit `skipped` rows for each downstream step and exit 0 → the final posting loop iterates ALL targets so already-replied items still appear in the result with their skip reason.
**Invariant:** The dedup check happens BEFORE navigation, content reads, and LLM calls — an already-replied URL costs zero page loads and zero tokens, not just a skipped final action. Zero-work is a SUCCESS exit carrying a complete step envelope (see step-result-envelope.md), not an error: "everything already done" is the normal steady state of a daily schedule.
**Probe:** No direct test for this executor (coverage caveat — source-grounded). Deterministic probes: grep pins `skippedDedup: repliedUrls.has(url)` at `x-search-reply.ts:316` and the zero-work `process.exit(0)` at `:323-330`; `linkedin-search-reply.ts:369-373` shows the identical convention; `search_graph --name-pattern "^(loadReplied|saveReplied)$"` resolves both symbols uniquely in x-search-reply.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "loadReplied saveReplied skippedDedup repliedUrls", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt boot-time Set construction, harvest-time flagging, new-only processing, and success-exit zero-work envelopes for ANY scheduled actor with persistent side effects. Adapt the store format and key (URL here; operation-log uses (platform, action, url)). Omit nothing — moving the check after navigation is the exact mistake this layout prevents (it burns reads and LLM tokens on already-done targets).
