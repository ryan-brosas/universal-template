<!-- capsule-v2 -->
# Pi tool-flag tri-state — when to emit `--no-tools`, `--tools <list>`, or omit the flag entirely

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `mnt-hdd-utopia-inspo-pi-ecosystem-veda`. **Question:** How does a driver map an agent's (sandbox, requested-tools) pair onto a CLI that distinguishes "no tools", "explicit allowlist", and "my own default full toolset" as three DIFFERENT wire states?

## toPiTools three-way return contract
**Path/Symbol:** `src/backend/pi.ts:toPiTools` (:46–81); consumer `PiBackend.run` flag-emission block (:102–110).
**Signature:** `function toPiTools(sandbox: SandboxMode, requestedTools?: string[]): string | undefined`.
**Data Shape:** Return is itself a tri-state wire command: `''` → emit `--no-tools`; a non-empty string → emit `--tools <value>`; `undefined` → emit NOTHING (pi's own default = complete toolset, "the only faithful full-access grant pi supports without naming every tool"). The v0.1.47 drift changed `sandbox==='full'` from returning `sandboxTools.join(',')` (a capped list) to returning `undefined`.

### Decisive source
```ts
export function toPiTools(sandbox: SandboxMode, requestedTools?: string[]): string | undefined {
  const baseTools = ['read', 'bash', 'grep', 'glob', 'list_threads', 'read_thread', 'todo_write', 'compact'];
  const sandboxTools = sandbox === 'read-only' ? baseTools : [...baseTools, 'edit', 'write'];
  if (requestedTools !== undefined) {
    if (requestedTools.length === 0) {
      return '';                                  // → --no-tools
    }
    if (sandbox === 'full') {
      // A full sandbox has no capability bound: pass the allowlist through
      return requestedTools.join(',');            // UNFILTERED (:59–63)
    }
    const allowed = new Set(sandboxTools);
    const filtered = requestedTools.filter(tool => allowed.has(tool));
    return filtered.length > 0 ? filtered.join(',') : 'read';   // :68 fallback
  }
  switch (sandbox) {
    case 'read-only':       return baseTools.join(',');
    case 'workspace-write': return sandboxTools.join(',');
    case 'full':            return undefined;     // omit --tools entirely (:76–79)
  }
}
```

```ts
// PiBackend.run (:102–110) — the return value selects among THREE arg shapes
const toolsArg = toPiTools(config.sandbox, config.tools);
if (toolsArg === '') {
  args.push('--no-tools');
} else if (toolsArg !== undefined) {
  args.push('--tools', toolsArg);
}
```

**Flow:** requestedTools defined? → empty=`''` / full-sandbox=unfiltered join / else intersect with sandbox allowlist (`read-only`=8 base tools, others=+`edit`,`write`) with least-capable `'read'` fallback when the intersection empties. requestedTools undefined? → sandbox switch decides: read-only/workspace-write get enumerated lists, **full gets `undefined` so pi's own default toolset applies**.
**Invariant:** The three outcomes are semantically distinct and none may be collapsed. Porting traps: (a) treating `''` and `undefined` alike either disarms the worker or fails to disable tools; (b) filtering a full-sandbox allowlist silently strips host-specific tools (the test pins `cdp`,`xtui` surviving); (c) `--no-tools` replaced the old `--tools ""` form — the comment notes it requires no patch anymore; (d) the empty-intersection fallback is deliberately the single weakest tool `'read'`, never an error.
**Probe:** `tests/backend/pi.test.ts` describe('toPiTools') — exactly 8 tests pin every polarity: `toPiTools('full')` `toBeUndefined()`; `toPiTools('full', ['read','bash','cdp','xtui'])` `toBe('read,bash,cdp,xtui')` unfiltered; `toPiTools('read-only', [])` `toBe('')`; `toPiTools('read-only', ['read','edit','write'])` `toBe('read')` (cannot expand capabilities); workspace-write+undefined contains edit/write/bash.
**Count check:** `awk '/describe\('"'"'toPiTools/,/^}\);/' tests/backend/pi.test.ts | grep -c 'test('` → 8; `grep -cF -- '--no-tools' src/backend/pi.ts` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "toPiTools sandbox allowlist no-tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state return→three-wire-shapes mapping and the full-sandbox pass-through/omit semantics for any backend that has a native "default everything" mode. Adapt the concrete base-tool names and the `'read'` fallback choice. Omit pi-specific flags once your backend exposes equivalent modes. Coverage note: pinned by the dedicated `toPiTools` suite at this commit; no integration test spawns a real pi process with the omitted flag.
