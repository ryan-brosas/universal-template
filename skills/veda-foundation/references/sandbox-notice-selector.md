<!-- capsule-v2 -->
# Sandbox-notice selector — the prepended capability notice must match runtime (tools, sandbox) exactly

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `mnt-hdd-utopia-inspo-pi-ecosystem-veda`. **Question:** How do you keep an agent's self-described permissions in its system prompt from drifting away from what its tool flags actually grant?

## withSandboxModeNotice pair-keyed selection over five notices
**Path/Symbol:** `src/agent/sandbox.ts:withSandboxModeNotice` (:117–138); five notice constants + idempotent prepend helpers :6–106; sole consumer `src/agent/persona.ts:resolveAgentConfig` (:277).
**Signature:** `function withSandboxModeNotice(systemPrompt: string, opts: { tools: string[] | undefined; sandbox: SandboxMode }): string`.
**Data Shape:** Five notices keyed by effective runtime state, not by persona name or config intent: no-access (`SANDBOX_NOTICE`), read-only, context-first read-only, workspace-write, and — new in v0.1.47 — full access (`SANDBOX_NOTICE_FULL`, :68–81). Every helper guards with `if (systemPrompt.includes('## Sandbox Notice')) return systemPrompt;` (5 such guard sites in the file) so double-prepending is impossible.

### Decisive source
```ts
export function withSandboxModeNotice(systemPrompt: string, opts): string {
  if (opts.tools === undefined) {
    // Full toolset granted (backend default) — e.g. the worker persona.
    if (opts.sandbox === 'full') return withFullSandboxNotice(systemPrompt);
    return opts.sandbox === 'workspace-write'
      ? withWriteSandboxNotice(systemPrompt)
      : systemPrompt;                       // read-only + undefined tools → NO notice
  }
  if (opts.tools.length === 0) {
    return withSandboxNotice(systemPrompt); // [] → no-access notice
  }
  // A specific allowlist: workspace-write still gets the write notice;
  // read-only stays unchanged.
  return opts.sandbox === 'workspace-write'
    ? withWriteSandboxNotice(systemPrompt)
    : systemPrompt;
}
```

The full-access notice itself (the text whose absence would mislead a full-sandbox worker):
```text
You are an AI assistant with **full access** to the local machine and network.
You may:
- Read, create, edit, and delete files anywhere
- Run any shell command, install packages, and start services when verification needs them
- Make network requests and drive external surfaces (browser, APIs)

Your permissions are **full** — no sandbox restricts you. ...
```

**Flow:** resolveAgentConfig computes the FINAL (tools, sandbox) pair first (after CLI overrides beat frontmatter beats global default), THEN calls this selector once at :277 so the prompt describes the resolved state — never the requested one.
**Invariant:** "Mismatch between notice and actual sandbox mode causes model confusion" (:2 header comment IS the invariant). The selector keys off the same tri-state tools vocabulary as `toPiTools`/`resolveAgentConfig` (`undefined` = full toolset vs `[]` = none); conflating them selects the wrong notice. Two deliberate asymmetries a porter will get wrong: (1) `read-only`+`undefined` gets NO notice at all (prompt untouched), while `[]` always gets the hard no-access notice; (2) an allowlist under `workspace-write` gets the write notice even though the allowlist is narrower — notice mirrors the sandbox bound, not the exact tool list.
**Probe:** No upstream test drives this file directly at this commit (deterministic anchors instead): `grep -c 'SANDBOX_NOTICE_FULL' src/agent/sandbox.ts` → 2 (definition + helper use); `grep -cF '**full access** to the local machine' src/agent/sandbox.ts` → 1; `grep -c "includes('## Sandbox Notice')" src/agent/sandbox.ts` → 5. Indirect behavior pin: `tests/agent/persona.test.ts:472` asserts the resolved worker systemPrompt contains `'full access'` and NOT `'no access to tools'`. Coverage caveat recorded in-capsule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "withSandboxModeNotice SANDBOX_NOTICE_FULL write notice", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pair-keyed selector + idempotent-prepend discipline for any agent host that tells the model what it may do. Adapt notice wording to your product's capability tiers. Omit nothing else — the value is that notices are DERIVED from resolved runtime state, never authored per persona. Coverage caveat: no dedicated unit suite for sandbox.ts at this commit; probes are deterministic source greps plus one indirect assertion in persona.test.ts.
