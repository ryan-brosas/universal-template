<!-- capsule-v2 -->
# ACP instruction mapping — how do you deliver host instructions into an opaque agent's config without prototype pollution or secret echo?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The host has system instructions for an ACP agent, but the agent's configuration surface is opaque — some agents read instructions from session metadata, others from a JSON blob inside a launch environment variable (e.g. a CODEX_CONFIG). How do you write the instructions into the declared channel safely?

## Fail-closed path-set into two channels
**Path/Symbol:** `packages/harness-acp/src/v1/bridge/instruction-mapping.ts` — `resolveACPInstructionConfiguration` (:13–59), `parseSerializableRecord` (:75–89), `setStringAtPath` (:91–113), `assertSafePath` (:115–125), `UNSAFE_PATH_SEGMENTS` (:7); wiring `bridge/index.ts` :381–391 (resolved before spawn, output feeds child env + newSession meta).
**Signature:** `resolveACPInstructionConfiguration({ instructions, instructionMapping, sessionMeta, environment }): Promise<{ sessionMeta; environment }>`; `setStringAtPath({ record, path, value }): Record<string, ACPSerializableValue>`.
**Data Shape:** `instructionMapping` = `{ type: 'session-meta' | 'launch-env-json', path: ReadonlyArray<string>, variable?: string }`. session-meta channel writes into the newSession `_meta`-adjacent sessionMeta record; launch-env-json channel parses `environment[variable]` as a JSON record, sets the path, and re-serializes into the same variable. Path guard: non-empty, every segment non-empty, no `__proto__`/`constructor`/`prototype`.

### Decisive source
```ts
// instruction-mapping.ts:75–89 — validated parse that never echoes the variable's contents
function parseSerializableRecord({ serialized, variable }) {
  try {
    const result = serializableRecordSchema.safeParse(JSON.parse(serialized));
    if (result.success) return result.data;
  } catch {}
  throw new Error(
    `ACP instruction mapping environment variable ${JSON.stringify(variable)} must contain a JSON object.`,
  );
}
```

**Flow:** no mapping, or empty instructions ⇒ inputs pass through untouched (sessionMeta and a copied environment). Otherwise the path is validated FIRST (fail before any mutation), then the channel branches: session-meta writes instructions at the path inside sessionMeta (defaulting `{}`); launch-env-json reads the existing variable (absent/empty ⇒ `{}`), parses it under a zod serializable-record schema, sets the path functionally, and JSON-stringifies the whole record back into the variable. The resolved environment is what the child agent is spawned with; the resolved sessionMeta rides the newSession request.
**Invariant:** the path guard runs before ANY write and rejects prototype-pollution segments outright (no silent coercion); existing env JSON that fails parse or schema validation throws a fixed message naming ONLY the variable name — the invalid contents (which may hold secrets) are never echoed, pinned by a dedicated test; setStringAtPath is purely functional (spread-rebuild at every level, never mutates the input record); non-record values encountered mid-path are replaced, not merged (last-writer-wins at that node); the instruction value is always a string — no object injection through the value channel.
**Probe:** `bridge/instruction-mapping.test.ts` (112L, 5 cases) — nested session-meta merge preserving sibling keys; launch-env merge into an existing CODEX_CONFIG preserving model/provider keys; variable-absent creation; the secret-safety case (invalid JSON containing a sentinel string must throw the fixed message whose String() does NOT contain the sentinel); `__proto__` path rejection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "resolveACPInstructionConfiguration setStringAtPath assertSafePath instructionMapping", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-channel instruction mapping (session metadata vs serialized launch-env JSON) for any agent whose config surface you do not control; adopt the three guards as a unit — prototype-pollution path rejection BEFORE mutation, schema-validated JSON parse of pre-existing config, and error messages that name the variable but never its contents. Adopt the functional path-set (spread-rebuild) so a failed mapping cannot half-mutate shared config. Adapt the channel set to your agents (add file-based or CLI-flag channels behind the same guard trio); omit the launch-env channel where the agent reads instructions from stdin or protocol metadata. Coverage caveat: fully test-pinned (5 cases); the pre-spawn wiring order (mapping resolved before spawn so the child never boots without its instructions) is deterministic-read-only.
