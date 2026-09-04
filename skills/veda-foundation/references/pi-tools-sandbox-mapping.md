<!-- capsule-v2 -->
# Pi tool-policy mapping — when does a full sandbox mean omitting --tools entirely, and why can an allowlist never EXPAND?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** How do you translate (sandbox mode, requested tools tri-state) into pi CLI's `--tools` / `--no-tools` flags without ever granting more than the sandbox allows — and what does the empty string vs undefined vs list encoding mean?

## (sandbox, tools) → CLI allowlist mapper
**Path/Symbol:** `src/backend/pi.ts` : `toPiTools` (:46-93), consumed by `PiBackend.run` (:110-118).
**Signature:** `function toPiTools(sandbox: SandboxMode, requestedTools?: string[]): string | undefined`.
**Data Shape:** Returns `''` → caller emits `--no-tools`; `undefined` → caller OMITS the flag entirely (= pi's own default complete toolset, the only faithful "full access" grant); `'a,b,c'` → `--tools a,b,c`.

### Decisive source
```ts
if (requestedTools !== undefined) {
    if (requestedTools.length === 0) {
      return '';                      // explicitly no tools → --no-tools
    }
    if (sandbox === 'full') {
      // A full sandbox has no capability bound: pass the allowlist through
      // unfiltered.
      return requestedTools.join(',');
    }
    const allowed = new Set(sandboxTools);
    const filtered = requestedTools.filter(tool => allowed.has(tool));
    // If after filtering nothing remains ..., fall back to least-capable read tool.
    return filtered.length > 0 ? filtered.join(',') : 'read';
  }

  switch (sandbox) {
    case 'read-only':       return baseTools.join(',');        // read,bash,grep,glob,list_threads,read_thread,todo_write,compact
    case 'workspace-write': return sandboxTools.join(',');     // baseTools + edit,write
    case 'full':
      // Full sandbox + full-toolset policy (the worker): omit --tools so pi
      // grants its own default (complete) toolset.
      return undefined;
  }
```

**Flow:** explicit `[]` beats everything → `--no-tools`; explicit list under `full` passes through UNFILTERED; explicit list under bounded sandboxes is intersected with the sandbox allowlist and collapses to the single least-capable tool `'read'` when nothing survives; NO requested tools → sandbox decides, where `full` uniquely means "omit the flag" because naming every tool of a self-updating CLI would rot. Base tools deliberately include `bash` for pi (user preference) and deliberately exclude GPT-specific `apply_patch`/`exec_command`.
**Invariant:** the mapping can only NARROW capabilities, never expand them — the only route to the full toolset is the undefined-tri-state path (`tools: all` persona + full sandbox); flattening `undefined` to `[]` anywhere upstream silently downgrades the worker to no tools ("the bug that surfaced as pi receiving --no-tools", test comment). Drift commit ddf808b added exactly this full-sandbox branch + its tests.
**Probe:** `tests/backend/pi.test.ts:63-107` — pins all three encodings incl. `toPiTools('read-only', ['read','edit','write'])` → `'read'` and `toPiTools('full', ['read','bash','cdp','xtui'])` → `'read,bash,cdp,xtui'`. Run: `bun test tests/backend/pi.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"toPiTools tools allowlist no-tools","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.backend.pi.toPiTools Function src/backend/pi.ts 46-93`.

## Verdict
Adopt the three-value return contract ('' | undefined | joined-list) and the narrow-only filtering rule verbatim — it is the reference shape for capability negotiation with any self-updating CLI. Adapt the concrete base-tool names to your backend's real toolset. Omit pi-specific flag spellings. Direct-test coverage strong at this pin (17 assertions in toPiTools describe block).
