<!-- capsule-v2 -->
# Init idempotence + dead config knobs — how does bootstrap avoid destroying existing memory, and which config options are decorative?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must know the exact init guard order (which files are never overwritten) AND which declared config fields actually do anything — porting the doc defaults verbatim ships a lie.

## Bootstrap guards + phantom config (`/memory:init`, `MemoryConfig`)
**Path/Symbol:** `pi-memory.ts` init handler (:370–478); `MemoryConfig` interface (:11–24); `DEFAULT_CONFIG` (:26–33).
**Signature:** init: `async (args: { scope?: "global" | "workspace" }, ctx) => void`.
**Data Shape:** Global scaffold = 7 dirs (user/facts/knowledge/state/inbox/archive) + index.md + placeholder-seeded files; workspace scaffold = root + inbox/archive + index.md.

### Decisive source
```ts
// Placeholder files: create-if-missing only — NEVER overwrite
const placeholder = "<!-- File is empty. Remove this comment to activate. -->\n";
for (const file of ["preferences.md", "coding-style.md", "tools.md"]) {
  const fp = path.join(config.globalDir, "user", file);
  if (!(await tryReadFile(fp))) await fs.writeFile(fp, placeholder, "utf-8");
}
...
// Workspace init refuses when sentinel exists
const existing = await tryReadFile(path.join(wsDir, "index.md"));
if (existing) { ctx.ui.notify("⚠ Workspace Memory already exists.", "warn"); return; }
```

**Flow (workspace):** git root required (warn+return outside a repo) → refuse if `index.md` exists → mkdir root/inbox/archive → write flat index. **Flow (global):** mkdir all seven dirs → overwrite-tolerant index write → seed placeholders ONLY where `tryReadFile` returns null.
**Invariant:** Init is IDEMPOTENT and destructive NOWHERE: directories via `recursive:true`, user files created only if absent, workspace aborts if already initialized. Placeholders double as zero-byte activation gates (scanner skips empty files). DEAD KNOBS: `config.priority` (:21,:31) is never read anywhere in the file, and `config.globalAlwaysInject` (:23,:32) is likewise declared-but-never-read — the tier order is hardcoded state>workspace>global inside `buildMemoryBlock`. Doc drift: design.md documents `globalAlwaysInject` default as `["user","knowledge"]` but code ships `["user","facts","knowledge"]`; README omits `facts/` from the global tree diagram while `/memory:init global` creates it. A porter who wires these knobs from docs ships behavior that does not exist.
**Probe:** NO upstream tests exist. Guard order verified by whole-file read; the never-read status of both knobs was verified mechanically this run (`grep -n 'globalAlwaysInject\|priority' pi-memory.ts` → matches ONLY at declaration + default sites :21/:23/:31/:32). Init handlers need host runtime; pure-side contracts covered by executed probes (GREEN).

## Get live surrounding code
**Retrieve:** graph BM25 has NO Function node matching `"init"` or `"current-task"` (anonymous closures + doc-token class), so resolve by content search instead:
```bash
codebase-memory-mcp cli search_code '{"project":"pi-memory-extension","pattern":"memory:init"}'
```
(Executed pass-3 audit at pin f3b4377f: rank-1 `pi-memory` Module lines **370;371;491** = registerCommand site + guard + already-exists warn; README/design.md Modules carry the doc hits.)

## Verdict
Adopt create-only-if-absent bootstrap with explicit refusal-on-existing for project scaffolds. OMIT the two phantom knobs (`priority`, `globalAlwaysInject`) or implement them for real — never ship them as documented-but-inert. Adapt directory taxonomy to host needs. Coverage caveat: no upstream suite; grep evidence recorded above.
