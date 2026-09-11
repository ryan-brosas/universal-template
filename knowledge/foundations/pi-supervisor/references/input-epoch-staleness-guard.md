<!-- capsule-v2 -->
# Input-epoch staleness guard — discarding decisions computed from a snapshot a user prompt has already superseded

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you prevent an expensive LLM verdict computed over old conversation state from steering after the user has typed something new?

## Two bump points, one comparison
**Path/Symbol:** `src/index.ts:82-91` (epoch declaration + two increment sites), consumed at :235 and :292-298.
**Signature:** `let userInputEpoch = 0` module-closure counter; bumped by `pi.on('input')` (interactive|rpc sources only) and `pi.on('before_agent_start')`.
**Data Shape:** Monotone integer in the extension closure; captured before await, compared after.

### Decisive source
```ts
let userInputEpoch = 0;

pi.on('input', (event) => {
  if (event.source === 'interactive' || event.source === 'rpc') {
    userInputEpoch++;
  }
});
pi.on('before_agent_start', () => {
  userInputEpoch++;
});
...
const inputEpochAtStart = userInputEpoch;
// ... await analyze(...) ...
if (userInputEpoch !== inputEpochAtStart) {
  updateUI(ctx, widgetState, state.getState(), { type: 'watching', ... });
  return;
}
```

**Flow:** capture epoch at settle-start → LLM analysis runs (seconds) → compare epoch again → mismatch ⇒ drop the computed decision entirely and render watching; match ⇒ act on steer/done.
**Invariant:** ANY user-visible input (typed message or new agent turn start) bumps the counter, so the guard fires even when the analysis itself triggered the next turn. The decision object is discarded, never partially applied — no intervention is recorded and no message is sent on the stale path.
**Probe:** `grep -c "userInputEpoch" src/index.ts` → 5 (declaration :82, input-bump :86, start-bump :90, capture :235, compare :292).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "extractThinking|truncateForNotify", query: "input epoch", limit: 5 });
```

## Verdict
Adopt capture-before-await / compare-after-await epoch guarding around every human-in-the-loop LLM decision. Adapt the bump events to whatever your host emits for real user activity (filter synthetic/system inputs at the bump site, as the source filter does). Omit nothing — the pattern is four lines and load-bearing.
