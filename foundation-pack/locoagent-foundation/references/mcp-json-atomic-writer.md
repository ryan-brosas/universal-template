<!-- capsule-v2 -->
# Atomic .mcp.json writer — how do I edit a shared JSON config file without losing permissions or corrupting it on crash?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the safe write sequence for `.mcp.json`, and which add-time validations run before any write?

## temp-file + datasync + rename + mode preservation
**Path/Symbol:** `src/services/mcp/config.ts`: `writeMcpjsonFile` (:88-131), reached from `addMcpConfig` (:625-761) and `removeMcpConfig` (:769-834).
**Signature:** `async function writeMcpjsonFile(config: McpJsonConfig): Promise<void>`; temp path `` `${mcpJsonPath}.tmp.${process.pid}.${Date.now()}` ``.
**Data Shape:** Writes `{ mcpServers }` only; on read-back scope metadata is stripped before persist (`const { scope: _, ...configWithoutScope }`).

### Decisive source
```ts
let existingMode: number | undefined
try { existingMode = (await stat(mcpJsonPath)).mode }
catch (e) { if (getErrnoCode(e) !== 'ENOENT') throw e }  // missing file = no perms to preserve

const handle = await open(tempPath, 'w', existingMode ?? 0o644)
try {
  await handle.writeFile(jsonStringify(config, null, 2), { encoding: 'utf8' })
  await handle.datasync()                 // flush to disk BEFORE rename
} finally { await handle.close() }
try {
  if (existingMode !== undefined) await chmod(tempPath, existingMode)
  await rename(tempPath, mcpJsonPath)     // rename uses ORIGINAL path: does not follow symlinks
} catch (e) {
  try { await unlink(tempPath) } catch {} // best-effort cleanup
  throw e
}
```

**Flow:** addMcpConfig validations IN ORDER: name charset `[^a-zA-Z0-Z9_-]` reject (:630), reserved builtin names reject (:636-648), enterprise-config-exists ⇒ exclusive-control reject (:651-655), zod schema validate (:658-664), denylist then allowlist policy checks with validated config so command-based enterprise rules can match (:667-679), per-scope duplicate check, finally scoped write (project → this file; user/local → global/project config stores).
**Invariant:** chmod BEFORE rename (temp file never carries wrong perms while visible under final name); datasync before rename (crash after rename never leaves truncated file); ENOENT on stat is success-not-error. The comment pins that rename "does not follow symlinks" — writing through a symlinked .mcp.json replaces the symlink.
**Probe:** `grep -n 'await handle.datasync()' src/services/mcp/config.ts` (`111:`) and `grep -nF ".mcp.json'" src/services/mcp/config.ts | head -3` (first hit line `89:` join path) and `grep -n 'existingMode ?? 0o644' src/services/mcp/config.ts` (`106:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "addMcpConfig", limit: 5 });
// writeMcpjsonFile resolves in the same module, cited line-exact
```

## Verdict
Adopt stat→open(mode)→datasync→chmod→rename→cleanup-on-fail ordering and the pre-write validation ladder. Adapt schema and scope stores. Omit product name-reserved lists.
