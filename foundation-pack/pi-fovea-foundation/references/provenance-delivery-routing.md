<!-- capsule-v2 -->
# Provenance delivery routing — when should drift steer NOW versus wait for the next prompt?

**Source:** pi-fovea MIT `main@5bd4e6f`; Codebase Memory `mnt-hdd-utopia-inspo-pi-fovea`. **Question:** A red sync verdict caused by ANOTHER session must not yank the current agent mid-task — where exactly does attribution flip the delivery channel, and what does each origin read like?

## kind → delivery + Origin line
**Path/Symbol:** `src/core/sync.ts:sync` (:592-603); consumers in `src/index.ts` (hook layer, :243/:327/:365 pass sessionId into every sync call).
**Signature:** `delivery?: "steer" | "next-prompt"` on `SyncOutcome` — immediate for current/mixed/unattributed work, deferred only for another session's.
**Data Shape:** `origin = provenance?.kind === "current-session" ? "current session" : "other-session" ? "another Fovea-enabled session" : "mixed" ? "mixed sessions or mutation paths" : "unattributed mutation path"`; message line `` `Origin: ${origin}.` ``; next-prompt action line = "Notice: review this concurrent update on the next prompt if it affects the task." vs steer's "Steer: account for this update before continuing."

### Decisive source
```ts
const delivery = provenance?.kind === "other-session" ? "next-prompt" : "steer";
...
...(provenance ? [`Origin: ${origin}.`] : []),
...
const actionLine = delivery === "next-prompt"
  ? "Notice: review this concurrent update on the next prompt if it affects the task."
  : "Steer: account for this update before continuing.";
```

**Flow:** every sync call passes the pi session UUID → `attributeChanges` classifies each drifted file → aggregate kind drives BOTH the outcome field (`delivery`) and the human-readable Origin line → host hook routes "steer" as an immediate injected context and "next-prompt" as queued intelligence attached to the following user message.
**Invariant:** Only "other-session" defers; mixed and even unattributed still steer immediately (an unknown actor changing YOUR working tree deserves attention now). The verdict is red either way — attribution changes WHEN the model sees it, never WHETHER. Missing sessionId ⇒ provenance undefined ⇒ plain steer (attribution is opt-in by caller).
**Probe:** `tests/extension.test.ts` — "delivers continuous sync intelligence as an immediate steer" (:501 pins `Origin: current session.`); "queues another session's relevant update for the next prompt" (:617 pins `Origin: another Fovea-enabled session.`); "keeps hidden sync intelligence model-visible without rendering it" (:708).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "SyncOutcome delivery next-prompt steer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the rule: attribution gates the CHANNEL, not the alarm. Adapt the two-channel vocabulary to your agent loop (e.g. interrupt vs inbox). Omit pi hook names.
