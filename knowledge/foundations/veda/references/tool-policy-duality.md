<!-- capsule-v2 -->
# Tool-policy duality — `undefined` means full toolset, `[]` means none; never coerce between them

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`; re-pinned pass 4 from `f050518c`); Codebase Memory `mnt-hdd-utopia-inspo-pi-ecosystem-veda`. **Question:** How must a request→backend config builder pass a tool policy through without silently disarming an agent?

> **ERRATUM (2026-08-24, v0.1.47 drift):** the sibling capsule `pi-tool-flag-tri-state.md` supersedes this one for the BACKEND side of the contract. The v0.1.47 drift removed the old `sandbox==='full' → sandboxTools.join(',')` cap in pi.ts — under a full sandbox the worker now gets pi's own default full toolset (flag OMITTED), and an explicit allowlist passes through UNFILTERED. This capsule's claim remains true at its own seam: buildBackendConfig (:45) is byte-identical at the new pin and the request→backend pass-through rule is unchanged. Read both; the tri-state vocabulary is shared.

## buildBackendConfig regression-proof pass-through
**Path/Symbol:** `src/core/llm.ts:buildBackendConfig` (:45–53); contract documented on `LlmRequest.tools` (:23–26); persona-side producer in `src/agent/persona.ts:resolveAgentConfig` (:259–270).
**Signature:** `function buildBackendConfig(req: LlmRequest): { model: string; reasoning: Reasoning; sandbox: Sandbox; tools?: string[]; systemPrompt: string }`.
**Data Shape:** Three-valued tool policy: `undefined` = backend's FULL toolset (worker's `tools: all`), `[]` = NO tools (advisory personas), non-empty list = explicit allowlist.

### Decisive source
```ts
/**
 * Build the backend AgentConfig from a request. Single derivation point for
 * tool policy: `tools: undefined` (worker's `tools: all`) reaches the backend
 * intact; `[]` stays "no tools" for the advisory personas. Never coerce
 * undefined to [] here — that silently strips the worker of its toolset.
 */
export function buildBackendConfig(req: LlmRequest) {
  return {
    model: req.model ?? '',
    reasoning: req.reasoning ?? ('medium' as Reasoning),
    sandbox: req.sandbox ?? ('read-only' as Sandbox),
    tools: req.tools,        // ← pass-through; the old `?? []` was THE bug
    systemPrompt: req.systemPrompt,
  };
}
```

**Flow:** persona frontmatter (`all`→undefined, `none`→[], csv→list) → CLI precedence `--no-tools > --tools > persona > [] default` in `resolveAgentConfig` → buildBackendConfig passes `tools` UNTOUCHED to every backend adapter. A historical `tools: req.tools ?? []` flattened worker `undefined` to `[]` — pi received `--no-tools` and the worker could not act.
**Invariant:** The three values are semantically distinct and must survive every layer byte-for-byte. Any `??` / `||` normalization at the boundary is a regression. Note the deliberate asymmetry in resolveAgentConfig: an unconfigured persona defaults to `[]` (safe), while persona `tools: all` maps back to `undefined` (full power).
**Probe:** `tests/core/llm-tools.test.ts` (:19–47) — five tests pin all polarities including `does not coerce missing tools to [] (the regression)` asserting `toBeUndefined()` AND `not.toEqual([])`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "buildBackendConfig tools undefined allowlist", limit: 10, fields: ["signature", "name", "file"] });
```
*(project name re-pointed to the path-slugged twin at the v0.1.47 re-pin; the short-name `veda` project serves the pre-drift graph and can no longer be refreshed in place.)*

## Verdict
Adopt the tri-state vocabulary and the no-coercion boundary rule for ANY agent-hosting config plumbing. Adapt field names/default reasoning levels. Omit nothing else — the entire value of this seam is what it refuses to do.
