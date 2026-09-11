<!-- capsule-v2 -->
# Vision engagement funnel — how does a provider turn a live social feed into exactly ONE AI-chosen engagement without ever repeating a past action?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** given an authenticated home timeline, how are candidate posts harvested, deduped against history, captioned by a vision model, gated by an LLM policy, and reduced to a single like+comment?

## DOM-harvest × API-truth join → screenshot captions → policy gate → single pick
**Path/Symbol:** `shared/server/bots/providers/x/x.provider.ts:likeAndCommentOnAPost` (:294-500); ledger write `shared/server/database/bots/bots.repository.ts:saveActions` (:56-72); ledger read `checkActions` (:76-122).
**Signature:** `likeAndCommentOnAPost(params: ParamsValue): Promise<ProgressResponse>`; harvest row `{ num, internalId, image: Buffer(jpeg q30), userUrl, following, followed_by }`.
**Data Shape:** candidates come from TWO planes joined client-side: DOM `article` scan gives `internalId` (status-id tail of `/status/…` href) + JPEG screenshot; the intercepted `/HomeTimeline` JSON supplies `relationship_perspectives.following/followed_by`, located by `entryId.indexOf(internalId) > -1`. Rows WITHOUT a resolvable relationship object are dropped entirely (`typeof following !== 'undefined'` guard) — no relationship truth ⇒ never a candidate.

### Decisive source
```ts
const obj = (
  entry?.content?.items?.[0]?.item?.itemContent?.tweet_results ||
  entry?.content?.itemContent?.tweet_results
)?.result?.core?.user_results?.result?.relationship_perspectives;
...
const checkUsed = await cursor.checkUsed(images.reduce((all, p) => [...all,
  ...list.map((type) => ({ id: p.internalId, type, userUrl: p.userUrl }))], []),
);                                   // BOTH action types checked per post
const notFound = checkUsed.filter((f) => !f.found);
...
const allowed = shuffle(await cursor.ai.getAllowedSubjects(subjects, ...))
  .filter((p) => p.allowed)?.[0];    // ONE uniformly-random survivor
```

**Flow:** intercept timeline response → scroll+scan every article (index kept as `num` for later re-scroll) → join DOM ids with API relationship flags → connection-select filter (`all` / `i-follow`=following / `following-me`=followed_by) → ask the ledger which `(id, type)` pairs were already done → drop used ones → vision-caption survivors (`pictureToText`) → policy-gate subjects → pick ONE shuffled survivor → re-scroll to its article index → like (+10s settle) then comment (AI-generated, typed with fast-typo `HumanTypingOptions`) → `cursor.saveActions(add)` persists BOTH actions → return `{delay:0, repeatJob:false, endWorkflow:true}`. Empty-after-dedupe or no-policy-survivor exits EARLY with `endWorkflow:true` (nothing more to do this cycle).

**Invariant:** dedupe is per `(botId, platform, type, internalId)` in the `savedActions` table — the SAME post can still receive its other action type (upvote and comment are separate ledger rows); `saveActions` writes AFTER the UI actions succeed, so a crash mid-funnel may redo one action but never skips persisting; the comment TEXT typed into the box travels separately: `cursor.ai.comment()` latches the post text into a closure variable (`bot.cursor.ts:35,:275`) and `saveActions` threads it as the `comment` column while the generated reply lands in `content` (`bots.repository.ts:65-71`). A porter who persists before clicking, or who treats the pair as one atomic unit, breaks either crash-recovery or auditability.

**Probe:** no upstream test runner (zero spec files repo-wide). Deterministic pins from repo root: `grep -nF 'entry?.content?.items?.[0]?.item?.itemContent?.tweet_results' shared/server/bots/providers/x/x.provider.ts` → :346; `grep -cF 'relationship_perspectives' shared/server/bots/providers/x/x.provider.ts` → 1; `grep -nF 'screenshot({' shared/server/bots/providers/x/x.provider.ts` → :360; `grep -cF 'checkUsed(' shared/server/bots/providers/x/x.provider.ts` → 1; `grep -nF 'saveActions(add)' shared/server/bots/providers/x/x.provider.ts` → :493.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "likeAndCommentOnAPost pictureToText", limit: 10 });
```

## Verdict
Adopt the funnel ORDER (harvest→join→dedupe→caption→gate→pick-one→act→persist) and the two-plane DOM/API join with drop-on-missing-relationship; adapt selector/testids, the specific timeline JSON path, and the connection-select vocabulary to your target site; omit the X-specific `HumanTypingOptions` fast-typo tuning (product anti-detection choice). Coverage caveat: deterministic probes only, no behavioral test suite exists upstream.
