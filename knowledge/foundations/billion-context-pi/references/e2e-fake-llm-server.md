<!-- capsule-v2 -->
# Fake OpenAI-compatible LLM server — how do you drive a real agent CLI end-to-end through a scripted model with zero network?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How must a porter script an LLM stub that exercises a full agent pipeline (context injection -> tool call -> state persistence) across MULTIPLE separate CLI invocations?

## File-based turn counter + auxiliary-call bypass + ref-driven compress ranges + SSE always
**Path/Symbol:** `scripts/e2e/fake-llm-server.cjs`: turn counter (:65-88), observations (:90-112), `extractMessageText`/`parseMessageRefs` (:116-161), `detectNudge` (:163-170), `resolveRange` (:184-192), SSE builders (:196-290), step handlers (:294-396), `handleRequest` (:400-474), routes (:478-492).
**Signature:** HTTP `GET /v1/models` (health) and `POST .../chat/completions` on 127.0.0.1:8400; env contract: `SCENARIO` (required, exit 2 without it), `TURN_COUNTER`, `OBSERVATIONS`, `PORT`.
**Data Shape:** scenario = `{turns: [{respond: "text"|"compress"|"nudge-compress"|"autonomous-nudge"|"decompress"|"search"|"tool", ...step fields}]}`; observations file = `{requests: [{turn, inputTokens, messageCount, compressCallCount, nudgeDetected, isAuxiliary}]}`.

### Decisive source
```ts
// :412-427 — requests WITHOUT tools are auxiliary host traffic (title/summary
// generation): canned reply, counter NOT advanced, observation turn:-1.
const hasTools = tools.length > 0;
if (!hasTools) { recordObservation({ turn: -1, ..., isAuxiliary: true }); textSSE(res, model, "ok", inputTokens); return; }
const nudgeDetected = detectNudge(messages);
const visibleCompressCount = countCompressCalls(messages);
const turnIdx = incrementCounter(TURN_COUNTER);   // file-based: survives new processes
const step = (scenario.turns || [])[turnIdx - 1];
```

**Flow:** every response is streamed as OpenAI-compatible SSE chunks (`data: {...}\n\n` terminated by `[DONE]`); tool_use is emitted as three deltas (announce with empty args -> full arguments string -> finish_reason "tool_calls"); text is split into ~10 word-grouped chunks. Compress steps first DISCOVER compressible refs by scanning the request's non-system messages for `<acp ...>mNNNNN</acp>` tags AND bracket-form `[mNNNN]` tolerance, deduped, including text hidden inside tool_call argument strings (:44-47, :127-161); if no refs are found the step falls back to plain text instead of failing. Range endpoints resolve against discovered refs with index clamping and support "all" (:184-192). nudge-compress steps emit context-growth text until the harness's nudge phrases appear in USER-role messages, then compress (:330-352); autonomous-nudge additionally counts its own emitted compress calls against a cap via a process-local counter (:354-383). Per-request telemetry lands in the observations file for the verifier.
**Invariant:** (1) the turn counter lives in a FILE, not memory — each non-auxiliary request advances it exactly once, so N scripted turns map onto N distinct `pi -p` invocations of one session. (2) Auxiliary (tools-less) requests never consume a turn — this is what keeps host bookkeeping invisible to the scenario timeline. (3) Ref discovery must read tool_call ARGUMENTS too, because injected acp tags ride inside them. (4) A missing scenario step degrades to plain text, never an error (:439-443).
**Probe:** repo's own harness command `npm run e2e -- <filter>` drives this server against real `pi -p` runs; health = GET /v1/models returning 200 with `{object:"list", data:[{id:"fake-model"...}]}` (:479-482). Static probe executed this pass: node syntax check plus the runner integration recorded in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "fake LLM server SSE turn counter nudge compress scenario", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: file-based turn counter keyed to non-auxiliary requests, the auxiliary bypass, discover-then-clamp compress ranges over injected refs, and degrade-to-text step dispatch when porting any scripted-model E2E rig. Adapt tag grammar and step vocabulary to your agent's tool names. Omit pi-specific nudge phrases (data, not contract).
