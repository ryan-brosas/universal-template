<!-- capsule-v2 -->
# Idle-nudge fallback — every analysis failure degrades to continue-or-nudge, never an exception out

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What should the supervisor do when its own LLM call fails, so the supervised agent is neither interrupted nor left stuck?

## Failure posture splits on idle
**Path/Symbol:** `src/core/analyzer.ts:20-58` (`analyze` catch arm :47-56).
**Signature:** `analyze(ctx, state, agentIsIdle: boolean, ineffectivePattern?, signal?, onDelta?): Promise<SteeringDecision>`.
**Data Shape:** Returns a synthetic low-confidence decision on failure instead of throwing: `{ action:'steer', message:'Please continue working toward the goal.', reasoning:'Analysis error', confidence:0 }` when idle, else `{ action:'continue', reasoning:'Analysis error', confidence:0 }`.

### Decisive source
```ts
  } catch {
    // When idle and analysis fails, nudge rather than silently do nothing
    return agentIsIdle
      ? { action: 'steer',
          message: 'Please continue working toward the goal.',
          reasoning: 'Analysis error',
          confidence: 0 }
      : { action: 'continue', reasoning: 'Analysis error', confidence: 0 };
  }
```
Upstream the session client enforces the same posture twice more (`src/session/client.ts:41,44`): failed session start and null prompt text both return `safeContinue(reason)`.

**Flow:** callSupervisorModel throws or session fails → catch → idle? nudge the agent forward : keep watching → the chat NEVER sees an extension exception.
**Invariant:** The fallback steer carries confidence 0 and NO asi — it is deliberately distinguishable from real verdicts and still flows through the normal steer branch (recorded + sent) because an idle agent with no input stays idle forever. A working agent gets `continue`, never a fabricated instruction.
**Probe:** `grep -c "Please continue working toward the goal." src/core/analyzer.ts` → 1; `grep -c safeContinue src/session/client.ts src/session/response-parser.ts` → 3 + 3 lines (definition + uses). Direct test: `tests/parsing.test.ts:83` "returns continue on invalid JSON", `tests/engine.test.ts:458-488` inferOutcome null arms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "parseDecision JSON fence markdown safeContinue", limit: 10 });
```

## Verdict
Adopt the split failure posture: errors become typed decisions, never exceptions crossing into the host app; only idle agents receive synthesized nudges. Adapt the nudge wording; keep confidence 0 so downstream logic can tell it apart. Omit nothing — this is the smallest capsule here but the one whose absence produces crashed extensions or wedged agents.
