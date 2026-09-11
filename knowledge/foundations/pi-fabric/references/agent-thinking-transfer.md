<!-- capsule-v2 -->
# Trajectory handoff + thinking transfer — how do you resume a child agent on a DIFFERENT model family without corrupting its session with foreign thinking signatures?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** which thinking blocks survive a cross-provider handoff, and how is the child's branch materialized without mutating the source session?

## Three-policy transfer over a cloned branch
**Path/Symbol:** `src/agents/thinking-transfer.ts` whole (:1-210); session materialization `src/agents/handoff.ts` (`snapshotHandoffSession` :134-172, `writeHandoffSession` :257-355, `persistedBranch` :223-238).
**Signature:** `thinkingTransferPolicy({source?, target}): "preserved"|"re-signed"|"stripped"`; `translateThinkingForExecutor(entries, policy): {entries, report}`; `buildThinkingDigest(entries, input)?: {content, citedBlocks}`.
**Data Shape:** policy inputs `{provider, modelId, api?}` ×2 plus target flags `reasoning?: boolean`, `requiresThinkingAsText?: boolean`; magic signature `REASONING_CONTENT_SIGNATURE = "reasoning_content"` (pi-ai uses the stored signature as the request FIELD NAME on openai-completions replay); digest bounds: newest 8 blocks, 80-char first lines, 2048-byte total, each line cited `[entry <id>]`.

### Decisive source
```ts
if (source && source.provider === target.provider &&
    (source.api === undefined || target.api === undefined || source.api === target.api))
  return "preserved";                                  // same provider+api: native replay
if (target.api === "openai-completions" &&
    target.reasoning === true && target.requiresThinkingAsText !== true)
  return "re-signed";                                  // normalize signature field
return "stripped";                                     // anthropic & friends: reject foreign sigs
// translate: toolCall parts lose `thoughtSignature`; re-signed keeps text and sets
// part.thinkingSignature = "reasoning_content" (skipping redacted/empty blocks)
```

**Flow:** at the fabric_exec boundary the host snapshots the leaf assistant turn (must contain ONLY the fabric_exec call — parallel top-level calls fail loudly), records outer tool result + current model/thinking-level from the tail of the branch → child side: preserved ⇒ cheap persisted fork via `createBranchedSession`; re-signed/stripped ⇒ read the exact prefix as a CLONE (raw line copy cannot rewrite signatures), translate, then materialize a fresh 0600 session file → stripped additionally appends the labeled digest ("deliberation, not commitments") as a custom entry → optional deterministic compaction is appended BEFORE settings-sync and the outer result so context opens summary-first → a `pi-fabric-handoff` audit entry records policy counts.
**Invariant:** the source session is NEVER mutated — all translation happens on structuredClone'd entries in a new file; unknown-apis degrade to preserved within one provider but to stripped across providers.
**Probe:** `tests/handoff.test.ts:61,129,182` pin fork/materialize/fail-on-parallel-batch; :202/:264 pin re-sign and strip+digest end-to-end; `tests/thinking-transfer.test.ts:62-110` pins every policy row, :195 pins digest citation format.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "thinkingTransferPolicy writeHandoffSession reasoning_content", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-policy taxonomy and clone-not-mutate materialization for any cross-model session handoff; adapt the signature token to your transport's convention; omit the compaction step if your handoffs are short. Direct tests cover all policies at unit and integration level — no coverage caveat.
