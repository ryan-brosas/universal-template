<!-- capsule-v2 -->
# Duplicate-send similarity guard — why is "already messaged this lead" decided by fuzzy string compare over the visible thread, not by the database?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** how does a messaging tool avoid double-sending when a job can re-run after crashes or queue replays?

## Read the rendered conversation, `compareTwoStrings > 0.95` ⇒ treat as already sent
**Path/Symbol:** `shared/server/bots/providers/x/x.provider.ts:sendMessage` (:163-218, check at :184-201); twin `shared/server/bots/providers/linkedin/linkedin.provider.ts:sendMessage` (:508-638, check at :584-605); engine `string-similarity`'s `compareTwoStrings` (dice coefficient).
**Signature:** `messages.allTextContents()` / `getAllMessages.allInnerTexts().map(trim)` → `some((p) => compareTwoStrings(p, data.message) > 0.95)` → return `{delay:0, repeatJob:false, endWorkflow:false}`.
**Data Shape:** X scans `[data-testid="messageEntry"]` texts; LinkedIn scopes `.msg-convo-wrapper` filtered by `hasText: "${lead.firstName} ${lead.lastName}"` then reads `.msg-s-event-listitem__body` innerTexts; both compare against the configured `data.message`.

### Decisive source
```ts
const allMessagesContent = await messages.allTextContents();
if (allMessagesContent.some(
    (p) => compareTwoStrings(p, data.message) > 0.95,
  )) {
  return { delay: 0, repeatJob: false, endWorkflow: false };   // NOT endWorkflow!
}
```

**Flow:** open DM surface → wait for existing message entries (10s timeout, empty-thread catch falls through to send) → if ANY prior message is ≥0.95 dice-similar to the intended text, STOP before typing. The outcome triple is load-bearing here: `endWorkflow:false` means "this step is fine, move on with the lead's campaign" — the lead continues to later steps, whereas a hard skip would have used `endWorkflow:true`.

**Invariant:** dedupe lives in the UI truth, not the DB: the `savedActions` ledger (see x-provider-vision-engagement-funnel) records upvotes/comments but NOT direct messages, so the thread itself is the source of truth for DMs. Threshold 0.95 tolerates platform-mangled whitespace/link-previews while still catching verbatim and near-verbatim repeats; it will NOT catch paraphrased follow-ups (that's what `x-send-followup-message` / `linkedin-send-followup-message`, gated by `allowedBeforeIdentifiers:['<send-message>']`, are for). LinkedIn additionally verifies delivery by waiting for the submit button to become DISABLED again (`button[type="submit"]:disabled`) rather than trusting the click.

**Probe:** deterministic pins from repo root: `grep -nF 'msg-convo-wrapper' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :577; `grep -cF 'compareTwoStrings(p, data.message) > 0.95' shared/server/bots/providers/x/x.provider.ts` → 1; `grep -cF 'compareTwoStrings' shared/server/bots/providers/linkedin/linkedin.provider.ts` → 2 (import + use); `grep -nF 'button[type="submit"]:not(:disabled)' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :619.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "compareTwoStrings allTextContents messageEntry", limit: 10 });
```

## Verdict
Adopt render-truth fuzzy dedupe with the ≥0.95 threshold and the `endWorkflow:false` continue-campaign outcome; adapt selectors/thread-scoping; omit the specific testids. Coverage caveat: deterministic probes only.
