<!-- capsule-v2 -->
# Verify-by-absence retry ladders and reason-coded failure JSON — how does a single-op executor prove an irreversible action landed and report failure without a human watching?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the retry/verify/report ladder for "click Post" when the only success signal available is that the compose box stopped containing your text?

## 3-attempt ref-refresh ladder; verify = text left the compose box; failures carry machine codes
**Path/Symbol:** `workflows/executors/post-hf-paper.ts` — post ladder `:146-183` (reason exits `:153`, `:174`, `:181`), URL-extract degrade `:203-207`, reply ladder `:228-250`, graded output `:252`; same ladder inline in `hf-papers-to-x.ts:460-483` (post) and `:410-431` (reply).
**Signature:** Ladder body per attempt: snapshot → regex `button "Post" \[ref=(e\d+)\]` → click → wait → scoped re-snapshot `snapshot -i -c -s '[role="textbox"]'`. Output: one final stdout JSON line `{ status: 'success', title, url, postUrl, replied }` or `{ status: 'failed', reason: 'post_button_not_found' | 'text_still_in_compose' | 'exhausted_retries' }`.
**Data Shape:** Success is tri-state on enrichment: `replied: true|false`, `postUrl: string|null` — main-post success with missing reply is still `status:'success'`.

### Decisive source
```ts
for (let attempt = 1; attempt <= 3; attempt++) {
  const snap = ab('snapshot -i -c')                       // fresh refs EVERY attempt
  const postMatch = snap.match(/button "Post" \[ref=(e\d+)\]/)
  if (!postMatch) { if (attempt === 3) { /* reason exit */ } ab('wait 2000'); continue }
  ab(`click @${postMatch[1]}`); ab('wait 5000')
  // Verify — compose box should be empty
  const verifySnapshot = ab(`snapshot -i -c -s '[role="textbox"]'`)
  if (!verifySnapshot.includes(title.slice(0, 20))) {     // ABSENCE of your text = landed
    posted = true; break
  }
}
...
console.log(JSON.stringify({ status: 'success', title, url: paperUrl, postUrl, replied }))
```

**Flow:** each attempt re-derives the button ref from a NEW snapshot (refs go stale after every mutation) → click → fixed settle wait → verify by observation: re-snapshot SCOPED to the textbox selector and assert your text's first 20 chars are GONE → absence proves submission because the platform clears a consumed composer. Button-not-found retries after a short wait; text-still-present retries the whole click. On exhaustion, exit non-zero with a reason code instead of a prose error. The self-reply repeats the identical ladder against `button "Reply"` with `'Paper:'` as its absence token. Enrichment steps that fail (URL extract, reply) downgrade to warnings + `replied:false`, never flip the top-level status.
**Invariant:** Verification is by ABSENCE in a scoped re-snapshot, not by trusting the click's exit code — a click can succeed while the site silently rejects the action. Refs are refreshed every attempt; never cache them across waits. Irreversibility asymmetry governs grading: once the main post lands, later step failures may not mark the operation failed (the dedup store would then wrongly allow a repost). Exactly ONE stdout line is the machine-readable contract; all narration goes to stderr.
**Probe:** No upstream executor tests. Deterministic source-grounded probes: reason-code exits at `post-hf-paper.ts:151-155` and `:172-176`, scoped verify at `:165-170`, tri-state success at `:252`. Coverage caveat recorded; port with a fake-driver unit test asserting the reason strings.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "postOnePaper composeTweet verify compose retry", limit: 10 });
```
Graph resolves `postOnePaper` :434-501 / `composeTweet` :342-360 (`hf-papers-to-x.ts`) line-exact; `post-hf-paper.ts` is a top-level script.

## Verdict
Adopt the fresh-ref-per-attempt ladder, scoped verify-by-absence, reason-coded failure JSON, and irreversible-step-dominates grading. Adapt wait durations, absence tokens, and reason vocabulary to your driver. Omit optimistic click-and-forget flows — without verify-by-absence you cannot distinguish "posted" from "clicked".
