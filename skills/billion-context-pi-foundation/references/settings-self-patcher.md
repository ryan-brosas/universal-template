<!-- capsule-v2 -->
# Settings self-patcher — how does an extension idempotently add its tools to a shared settings.json without corrupting user edits?

**Source:** billion-context-pi (MIT) `master@558a83a9db69`; Codebase Memory project `billion-context-pi`. **Question:** What write protocol lets an extension merge entries into a user-owned JSON file safely under concurrency?

## Read → mtime stamp → merge → one-time backup → mtime recheck → tmp+rename → verify → restore-on-fail
**Path/Symbol:** `src/setup-subagent-tools.ts`: `ensureSubagentAcpTools` (:47-136), `desiredTools` (:37-45), `BUILTIN_DEFAULT_TOOLS` (:10-20).
**Signature:** `ensureSubagentAcpTools(settingsPath?) -> {path, action: "skipped"|"updated"|"failed", reason?}`.
**Data Shape:** target = `<agentDir>/settings.json` under `subagents.agentOverrides.<name>.tools`; injected tools = ACP_TOOLS (`compress/decompress/search_context/acp_status`); every builtin role's default allowlist is tabulated in-code.

### Decisive source
```ts
// :92-104 — optimistic concurrency + first-write backup:
const backupPath = `${path}.acp-bak`;
if (!existsSync(backupPath)) {
  try { await copyFile(path, backupPath); } catch { /* best effort */ }
}
// Optimistic concurrency guard: bail if the file changed since we read it.
if ((await stat(path)).mtimeMs !== mtimeMs) {
  return { path, action: "skipped",
    reason: "settings.json changed during setup (concurrent write); will retry next session" };
}
```

**Flow:** missing file → skip (retry next session; never create the host's settings). Invalid JSON / non-object root → fail without writing. Merge rule preserves user customization: existing non-empty `tools` array is kept and only MISSING ACP tools appended (no duplicates, no reordering); empty/absent → builtin defaults + ACP tools. Write via `${path}.tmp-${pid}` + rename (atomic). Then RE-READ and VERIFY all agents carry the tools — verification failure copies `.acp-bak` back over the file.
**Invariant:** (1) idempotent — second run is a skip with zero writes (backup also NOT overwritten after first creation). (2) The mtime captured at read time must be re-checked immediately before write; a mismatch aborts toward retry-later rather than clobbering a concurrent writer. (3) User-customized tool arrays are append-only-merged, never replaced. (4) Every failure path leaves the file either untouched or restored to backup.
**Probe:** `tests/setup-subagent-tools.test.ts:32-135`: creates overrides when none (:32), idempotent skip (:44), preserves customized tools + appends (:57), no duplicates when partially present (:76), preserves other fields like model/thinking (:93), invalid JSON fails untouched (:111), missing file skipped (:123), backup created on FIRST write only (:132).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "billion-context-pi", query: "ensureSubagentAcpTools desiredTools agentOverrides", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full protocol for ANY extension that patches shared config files — it is a complete safety ladder with a dedicated test per rung. Adapt the target path/shape to your config surface. Omit the builtin-role table (host-specific data).
