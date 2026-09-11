<!-- capsule-v2 -->
# Sandbox-notice selection — which notice text matches an effective (tools, sandbox) pair without lying to the model?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** When a porter composes a system prompt for a spawned CLI agent, how must the sandbox notice be chosen so it never claims capabilities the runtime will not grant (or hides ones it will)?

## Sandbox notice selector
**Path/Symbol:** `src/agent/sandbox.ts` : `withSandboxModeNotice` (:117-138) with five notice constants and one wrapper per mode (`withSandboxNotice` :64, `withReadOnlySandboxNotice`, `withReadOnlyContextFirstNotice`, `withWriteSandboxNotice`, `withFullSandboxNotice` :103).
**Signature:** `function withSandboxModeNotice(systemPrompt: string, opts: { tools: string[] | undefined; sandbox: SandboxMode }): string`.
**Data Shape:** `SandboxMode = 'read-only' | 'workspace-write' | 'full'`; `tools` is the RESOLVED tri-state policy: `undefined` = backend's full toolset granted, `[]` = no tools, list = allowlist (see persona/tool-policy capsules). Returns the prompt with the matching notice prepended, idempotently.

### Decisive source
```ts
export function withSandboxModeNotice(
  systemPrompt: string,
  opts: { tools: string[] | undefined; sandbox: SandboxMode }
): string {
  if (opts.tools === undefined) {
    // Full toolset granted (backend default) — e.g. the worker persona.
    if (opts.sandbox === 'full') return withFullSandboxNotice(systemPrompt);
    return opts.sandbox === 'workspace-write'
      ? withWriteSandboxNotice(systemPrompt)
      : systemPrompt;
  }
  if (opts.tools.length === 0) {
    // Explicitly no tools — no-access notice matches runtime.
    return withSandboxNotice(systemPrompt);
  }
  return opts.sandbox === 'workspace-write'
    ? withWriteSandboxNotice(systemPrompt)
    : systemPrompt;
}
```

**Flow:** resolved tools `undefined` → full toolset branch: `full` sandbox gets the FULL notice ("no sandbox restricts you"), `workspace-write` gets WRITE, `read-only` gets NO notice; resolved tools `[]` → always the no-access notice regardless of sandbox; non-empty allowlist → workspace-write gets WRITE notice, everything else gets NO notice. Every wrapper first checks `systemPrompt.includes('## Sandbox Notice')` and returns unchanged — double-prepend impossible when composing layered prompts.
**Invariant:** "The notice must match runtime reality" (file header comment) — a mismatch between notice and actual capability causes model confusion; the empty-vs-undefined allowlist distinction is load-bearing here exactly as in `resolveAgentConfig`. Introduced by drift commit 2f9de50 (worker defaults to full sandbox + full toolset): before this commit the worker got no notice while running unsandboxed.
**Probe:** `tests/agent/persona.test.ts` + `tests/backend/pi.test.ts:63-107` (pins `toPiTools('full', undefined)` → `undefined` = omit flag = pi default full toolset; `toPiTools('read-only', ['read','edit','write'])` → `'read'` = least-capable fallback). Run: `bun test tests/backend/pi.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"sandbox notice full toolset","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.agent.sandbox.withSandboxModeNotice Function src/agent/sandbox.ts 96-116`.

## Verdict
Adopt the (tools-tri-state × sandbox-mode) selection matrix and the idempotence marker check verbatim — it is pure string logic. Adapt notice prose wording to your host's effect channels. Omit the five hardcoded notice texts if your agent framework communicates capability structurally instead of via prompt text. Coverage caveat: no upstream test drives `withSandboxModeNotice` directly (persona tests pin its inputs); behavior verified by source read at pin.
