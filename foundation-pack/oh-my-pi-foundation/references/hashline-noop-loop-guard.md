<!-- capsule-v2 -->
# Hashline noop loop guard — how do you break a subagent loop on byte-identical no-op edits?

**Source:** Oh My Pi MIT `main@96f42809764f0907f7d6b115eab5710de28941de`; Codebase Memory `oh-my-pi`. **Question:** When an edit applies cleanly but changes nothing, how do you stop the model from re-issuing the same payload forever?

## Consecutive-identical-noop counter escalating soft hint → hard tool error
**Path/Symbol:** `packages/coding-agent/src/edit/hashline/noop-loop-guard.ts:recordNoopEdit` (71–81), `resetNoopEdit` (87–91), `hashPatchInput` (97–99), `NOOP_HARD_LIMIT = 3` (40), `NoopLoopGuard` session slot (29–50); escalation call sites `execute.ts` `executeHashlineSingle` (246–253 single-section, 271–293 multi-section), soft-hint text `noChangeDiagnostic` / loop diagnostic `noChangeLoopDiagnostic` (`execute.ts:73`).
**Signature:** `function recordNoopEdit(session: NoopLoopGuardOwner, canonicalPath: string, inputHash: string): { count: number; escalate: boolean }`; `function resetNoopEdit(session, canonicalPath): void`; `function hashPatchInput(input: string): string`.
**Data Shape:** per-session state slot `{ entries: Map<canonicalPath, { hash: string; count: number }> }` lazily created on the ToolSession (mirrors `getFileSnapshotStore`); `inputHash` is xxHash64 (`Bun.hash`) of the RAW model-authored patch bytes; `escalate = count >= 3`.

### Decisive source
```ts
// Same raw bytes again on this path ⇒ count up; ANY different payload resets
// to 1 — a changed body hash is model progress and earns a fresh soft hint.
const prev = guard.entries.get(canonicalPath);
const count = prev && prev.hash === inputHash ? prev.count + 1 : 1;
guard.entries.set(canonicalPath, { hash: inputHash, count });
return { count, escalate: count >= NOOP_HARD_LIMIT };
// execute.ts: the first two no-ops return soft TEXT ("parsed and applied
// cleanly, but produced no change … re-read the file"); on escalate it is a
// thrown ToolError so the agent loop sees a tool FAILURE.
if (sectionResult.op === "noop") {
    const { count, escalate } = recordNoopEdit(options.session, sectionResult.canonicalPath, inputHash);
    if (escalate) throw new ToolError(noChangeLoopDiagnostic(sectionResult.path, count));
    return renderSection(sectionResult, undefined, prepared.section.path).toolResult;
}
resetNoopEdit(options.session, sectionResult.canonicalPath); // after any real commit
```

**Flow:** commit returns `noop` → hash the raw input bytes → record against the canonical path → below limit: render the actionable soft diagnostic and return normally → at limit (3rd consecutive identical): throw `ToolError` with the repeat count → any non-noop commit for that path calls `resetNoopEdit`, so the next no-op starts over at the soft hint.
**Invariant:** the counter keys on RAW INPUT bytes, not file content — whitespace-only respins count as progress by design ("re-issuing the same bytes after being warned is what we want to break"); state never leaks across canonical paths or sessions; escalation converts an ignored hint into an agent-loop-visible failure. Motivating evidence in-source: issue #2081 captured 182 identical repeats in 205 calls before user abort.
**Probe:** `packages/coding-agent/test/core/hashline-loop-guard.test.ts:79` ("escalates to a thrown ToolError on the Nth consecutive byte-identical no-op"), `:62` (first `NOOP_HARD_LIMIT - 1` attempts stay soft), `:132` (counter resets after a successful non-noop commit), `:106` (no accumulation across distinct paths), `:168` (per-session isolation). Soft-text contract at `packages/coding-agent/test/core/hashline.test.ts:164` ("byte-identical to the file" + "re-read the file", file untouched).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^recordNoopEdit$|^NOOP_HARD_LIMIT$|^executeHashlineSingle$", limit: 10 });
```

## Verdict
Adopt the pattern verbatim for ANY idempotent-looking tool that can silently succeed-without-effect (edit, shell, API POST): per-target slot + raw-input hash keying + small limit (3) + soft-hint-first escalation into a thrown tool error + reset-on-real-progress; adapt the hash function to your runtime and the hint/error wording to your UX; omit nothing — the module is host-free except the Bun hash.
