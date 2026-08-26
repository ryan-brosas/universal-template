<!-- capsule-v2 -->
# Interruption envelope + resume — how do approvals/clarifications/secrets survive process death?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter implementing human-in-the-loop pauses must serialize just enough engine state, classify pauses into a UI-safe taxonomy, and replay resolutions exactly once.

## Envelope + taxonomy + resume ladder
**Path/Symbol:** `agent-runtime/src/sdk-engine.ts:serializeState` (:453-460), `parseSerializedState` (:462-490), `runtimeInterruptionFromSdk` (:610-650), `OpenAIAgentsEngine.resume` (:167-207); types in `types.ts` (`RuntimeInterruption` :99-132, `InterruptionResolution` :64-80).
**Signature:** `serializeState(sdkState: string, reasoningWireFormat?): string`; `resume(input): Promise<EngineResult>`.
**Data Shape:** Three-kind taxonomy — `approval{id,callId,toolName,arguments,approvalPresentation?,approvalBinding?}`, `clarification{question,choices[]}`, `secret{reason}` (NEVER a value).

### Decisive source
```ts
const serializedState = interruptions.length > 0
  ? serializeState(stream.state.toString(), modelProvider.reasoningWireFormat)
  : undefined;
// envelope: { clovyVersion:1, juneVersion:1, sdkState, reasoningWireFormat? }
// parseSerializedState FAILS OPEN: unknown version or non-envelope JSON →
//   { sdkState: serializedState }  ("Older interruptions stored the raw SDK state string.")

if (toolName === REQUEST_CLARIFICATION_TOOL.name) return { kind:"clarification", question..., choices };
if (toolName === "request_secret") return { kind:"secret", reason };   // no value field exists

// resume:
const state = await RunState.fromString(agent, persistedState.sdkState);
for (const resolution of input.params.resolutions) {
  const interruption = interruptions.find(i => interruptionId(i) === resolution.interruptionId);
  if (!interruption) throw new Error(`Unknown interruption: ${resolution.interruptionId}`);
  if (resolution.kind === "clarification"
      || (resolution.kind === "secret" && resolution.decision === "approve")
      || resolution.decision === "approve") state.approve(interruption);
  else state.reject(interruption, message ? { message } : undefined);
}
```

**Flow:** Stream ends paused → map every SDK interruption through the taxonomy (arguments parsed then SANITIZED — `parsedToolArguments` runs `sanitizeForLog`, so approval previews cannot echo secrets) → service emits usage THEN `interruption.requested{serializedState,usage}` → host persists → later `run.resume{serializedState,resolutions}` → approve/reject replay → the SAME stream continues; the pending tool finally executes against the host.
**Invariant:** State is serialized ONLY when interruptions exist (clean runs stay small); unknown interruption ids are loud errors, not skips; secret approvals carry decisions but never values (test asserts no `secretValue` key anywhere in the payload — the actual value enters via the host keychain boundary, outside model context); Notion-style tools add an input-guardrail preflight before pause AND again before approved execution — preflight results are cached under `${runId}:${callId}`, consumed exactly once into `approvalPresentation`+`approvalBinding{digest}` at interruption mapping, and same-run leftovers are pruned at stream settle (full lifecycle: `notion-preflight-cache-binding`).
**Probe:** `agent-runtime/test/sdk-tool-loop.test.ts` "resumes a serialized approval and continues after the host tool result" (:988-1140, asserts envelope versions and single tool execution) and "preflights a Notion action before interruption and again before approved execution" (:1142-1282); `agent-runtime/test/secret-interruption.test.ts` "maps request_secret pauses without including a secret value". Suites runner-blocked at pin; ranges read directly.

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"interruption approval clarification secret serialized state resume", file_pattern:"agent-runtime/*" })
→ src.sdk-engine.parseSerializedState Function sdk-engine.ts 462-490  (rank 1)
   src.service.RuntimeService.resume Method service.ts 160-183
   src.sdk-engine.OpenAIAgentsEngine.resume Method sdk-engine.ts 167-207
   src.sdk-engine.runtimeInterruptionFromSdk Function sdk-engine.ts 610-650
```

## Verdict
Adopt serialize-only-on-pause, versioned envelopes that fail open to raw-state parsing, the three-kind taxonomy, and loud unknown-resolution errors. Adapt the envelope keys to your product (keep BOTH a semantic key and a legacy alias during migration, as `clovyVersion`/`juneVersion` do). Omit the Notion preflight unless you have an equivalent "show the user what will happen before they approve" requirement — then port it whole, including the callId binding.
