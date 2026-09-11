<!-- capsule-v2 -->
# Follow-button detach handshake — what is the wait-ladder that turns a fragile UI click into a confirmed state transition?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** after `cursor.click()` (humanized bezier click) returns, how does the provider KNOW the action registered, and what does it do when the surface is missing?

## visible-wait → humanized click → detached/disabled confirmation → outcome triple
**Path/Symbol:** `shared/server/bots/providers/x/x.provider.ts:followConnection` (:117-141, ladder :126-140); send-path confirmations :181-211 (`toBeDisabled` :210); LinkedIn delivery twin `linkedin.provider.ts:sendMessage` (:618-631); DM-surface-missing early-exit x.provider.ts :170-178.
**Signature:** `followConnection(params, lead): Promise<ProgressResponse>` — pattern: `waitFor({state:'visible', timeout})` → `timer(5000)` → `cursor.click(btn)` → `btn.waitFor({state:'detached', timeout})`.
**Data Shape:** X follow button located by testid regex `/^\d+-follow$/` inside `[data-testid="primaryColumn"]`; success = button LEAVES the DOM; X send success = composer send button reports DISABLED after Enter (message left the box).

### Decisive source
```ts
const followButton = params.page.getByTestId('primaryColumn').first()
  .getByTestId(/^\d+-follow$/).first();
await followButton.waitFor({ timeout: 60000, state: 'visible' });
await timer(5000);
await params.cursor.click(followButton);            // bezier mouse path
await followButton.waitFor({ timeout: 60000, state: 'detached' });  // proof
```

**Flow:** visibility gate (60s) → fixed 5s settle → ghost-cursor click → terminal-state wait (`detached`) → return `{delay:0, repeatJob:false, endWorkflow:true}` (a follow ENDS that lead's workflow). The messaging twin inverts two details: surface-missing (`sendDMFromProfile` never visible within 60s) exits with `endWorkflow:true` BEFORE typing, and post-send confirmation waits for the send button's DISABLED state instead of detachment.

**Invariant:** every state-changing UI action pairs ONE pre-wait with ONE post-proof, and the proof predicate matches the widget's real physics (follow buttons vanish on toggle; send buttons disable when their textarea empties) — porters who substitute `expect(...).toBeVisible()` checks for the post-proof re-introduce silent no-op clicks. The interstitial `timer(5000)` calls are not decoration: they separate bot-like instant chains and let SPA transitions settle before the next locator resolves. All failure paths still return ProgressResponse triples rather than throwing, because the throttler treats a thrown activity as retry-with-cap-3 while an explicit triple encodes intent.

**Probe:** deterministic pins from repo root: `grep -n "state: 'detached'" shared/server/bots/providers/x/x.provider.ts` → :134; `grep -nF 'primaryColumn' shared/server/bots/providers/x/x.provider.ts` → :127; `grep -cF 'toBeDisabled()' shared/server/bots/providers/x/x.provider.ts` → 1; `grep -cF 'sendDMFromProfile' shared/server/bots/providers/x/x.provider.ts` → 1; `grep -nF 'button[type="submit"]:not(:disabled)' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :619.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "followButton waitFor detached cursor click", limit: 10 });
```

## Verdict
Adopt the visible→click→proof handshake with physics-matched predicates; adapt locators/timeouts to your target; omit the specific settle durations if your host measures its own. Coverage caveat: deterministic probes only.
