<!-- capsule-v2 -->
# fabric_exec result assembly — output budget with artifact spill, media re-attachment, and terminate/handoff settlement

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how does the raw sandbox run become the model-visible tool result (and terminal preview) at the end of `execute()`?

## Connected graph-selected seam
**Path/Symbol:** `src/fabric-exec-tool.ts:execute` (:671-853) — media re-attachment (:800-845), terminate detection (:793-799), type-error early return (:766-786), handoff claim (:707-719); `src/output-budget.ts:modelOutputBudget` (:8-13), `boundModelOutput` (:31-58); `src/failure-progress.ts:formatFailureProgress` (:12-33).
**Signature:** `modelOutputBudget(configuredMaxChars, success)` → success ? configured : min(configured, 20_000); `boundModelOutput(visible, maxChars, fullOutput = visible)` → `{ text, artifactPath?, originalChars, omittedChars }`; `formatFailureProgress(trace)` → string | undefined.
**Data Shape:** sections joined `\n\n` as `[logs, formattedValue, "Runtime error: …", failureProgress]`; artifact `{ tmpdir()/pi-fabric-output-*/, output.txt, mode 0o600 }`; content array mixes `{type:"text"}` with FabricMediaBlock image blocks.

### Decisive source
```ts
      const mediaBlocks: FabricMediaBlock[] = [];
      for (const audit of result.audits) {
        if (audit.media) mediaBlocks.push(...audit.media);   // collected OOB per call
      }
      ...
      // The base64 payload now lives in the result content; discard the
      // duplicate in-memory audit copies before returning.
      for (const audit of result.audits) {
        delete audit.media;
        delete audit.mediaNote;
      }
```

**Flow:** on success/failure the full model-bound text = logs + formatted value + runtime error + failure progress; the budget is computed from CONFIG for successes but clamped to 20k for failures — a crashing run can never flood the context. Over-budget output spills to a 0600 tempdir artifact and the visible text gets `[Full output (N chars) saved to: …]` appended BEFORE truncation so the suffix itself is inside the budget (`bodyBudget = maxChars − suffix.length`, middle-truncated). Type errors short-circuit: "code was not executed" + recovery hint, `isError: true`. A pending prewalk handoff is claimed into `pendingHandoffs` keyed by toolCallId and forces termination; an explicit `{ terminate: true }` return value does too. Nested `pi.read` images arrive OUT-OF-BAND on each call audit (the LLM-bound clone got descriptions instead); execute() re-collects them into the RESULT content blocks (terminal renders kitty previews) while deleting the base64 duplicates from audits before persisting.
**Invariant:** the model never sees more than the budget under any outcome; artifact persistence failure degrades to bounded text, never an error; media moves audit→content exactly once (no double storage in details); single-call reads swap the body text for the read's own clean note rather than the handoff description; `failureProgress` lists completed calls' refs+paths ONLY ("outputs not returned") capped at 8 calls/100-char paths with the warning that mutations may already have landed — it is absent for successful traces or failures with zero completed calls.
**Probe:** `tests/output-budget.test.ts:29` ("bounds visible text and links the complete artifact"), `:43` ("persists retrievable artifacts with private POSIX permissions"), `:53` ("stays bounded if artifact persistence fails"); `tests/failure-progress.test.ts:27` ("reports completed refs and paths without exposing results"). Media re-attachment has NO dedicated upstream suite (behavior pinned only by in-source comments :800-807/:813-819 — port from source, not tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "fabric_exec boundModelOutput mediaBlocks attachMedia terminate pendingHandoff", limit: 5, fields: ["signature", "name", "file"] });
```
