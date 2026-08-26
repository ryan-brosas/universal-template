<!-- capsule-v2 -->
# Subagent tool injection — how does an extension add its tools to ANOTHER package's agents without clobbering user overrides or resurrecting stale state?

**Source:** billion-context-pi (MIT) `master@6a88c5565355`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** How must a porter detect an external agent-package install, discover its shipped agents, and merge capability tools into user-owned overrides safely?

## Detect install -> discover frontmatter -> base-wins merge -> backup-once -> mtime recheck -> tmp+rename -> verify-or-restore
**Path/Symbol:** `src/setup-subagent-tools.ts`: `findPiSubagentsInstall` (:96-128), `parseFrontmatterTools` (:61-81), `discoverBuiltinAgents` (:135-154), `desiredTools` (:156-163), `ensureSubagentAcpTools` (:169-290); command wiring `src/commands.ts` `acp-subagents` (:91-104). Supersedes the pre-f30363d settings-self-patcher contract (BUILTIN_DEFAULT_TOOLS defaults are gone).
**Signature:** `ensureSubagentAcpTools(settingsPath?, options?: {agentDir?, cwd?, installDir?}) -> {path, action: "skipped" | "updated" | "failed", reason?}`.
**Data Shape:** target = `<agentDir>/settings.json`, keys under `subagents.agentOverrides.<name>.tools`; injected set = ACP_TOOLS (`compress/decompress/search_context/acp_status`, :18); discovered builtins = `{name, tools?}` where a missing `tools` line means UNRESTRICTED.

### Decisive source
```ts
// :222-239 — patch ONLY agents the installed package ships; an existing user
// override is the BASE (customization beats frontmatter); unrestricted agents
// get no override entry at all:
const frontmatterByName = new Map(builtins.map((b) => [b.name, b.tools]));
for (const name of builtins.map((b) => b.name)) {
  const existing = overrides[name];
  const baseTools =
    existing?.tools && Array.isArray(existing.tools) && existing.tools.length > 0
      ? existing.tools
      : frontmatterByName.get(name);
  if (baseTools === undefined) continue; // Unrestricted agent — nothing to grant.
  const wanted = desiredTools(baseTools);
  ...
}
```

**Flow:** runs ONLY on the explicit `/acp-subagents` command, never at session start (module header :1-4; commands.ts :95 "re-run after upgrading pi-subagents"). Detection ladder (:96-128): user npm `<agentDir>/npm/node_modules/pi-subagents` -> project npm `<cwd>/.pi/npm/node_modules/pi-subagents` -> extension-dir scans (`<agentDir>/extensions`, `<cwd>/.pi/extensions`) matching a directory whose package.json `name === "pi-subagents"` (unreadable entries skipped) -> explicit `options.installDir` bypasses detection but must contain package.json (:175-179). Discovery reads `<install>/agents/*.md` frontmatter for name + comma-separated tools (:135-154); no agents dir -> skip. Missing settings.json -> skip; invalid JSON / non-object root -> failed WITHOUT writing (:199-207). Merge appends only MISSING ACP tools onto the base list, order-preserving and deduped (:156-163). Write ladder (:250-289): copy-once backup `${path}.acp-bak` -> capture `statSync(path).mtimeMs` AFTER backup -> write `${path}.tmp-${pid}` -> re-check mtime, unlink tmp + return failed on mismatch -> rename -> RE-PARSE the written file and verify every restricted shipped agent carries all ACP tools, restoring the backup on verification failure.
**Invariant:** (1) scope discipline — only agents the installed package actually ships are patched; overrides for unknown/stale agent names are preserved byte-for-byte (#179 regression: "never recreates the stale 9-agent set"). (2) Unrestricted agents never gain an override entry. (3) Idempotent — a complete state is a zero-write skip; the backup is never overwritten after its first creation. (4) Failure atomicity — every failure path leaves the file untouched or restored from `.acp-bak`. (5) A detection miss is a SAFE no-op: git installs and the legacy global npm location are deliberately unchecked (:93-94).
**Probe:** `tests/setup-subagent-tools.test.ts` — skip-without-touch when not installed (:62-89); four-tier detection incl. extensions dir and explicit installDir (:91-137); not-a-package clear failure (:139-145); no-agents skip (:147-157); stale-set preservation (:159-179); base-wins append with non-tools fields kept (:183-199); partial completion without reordering (:201-216); idempotent second run byte-equal (:218-228); backup created once and kept across later updates (:230-241); missing-file skip and invalid-JSON-fails-untouched (:245-261).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "findPiSubagentsInstall discoverBuiltinAgents ensureSubagentAcpTools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: detect-before-touch (miss = no-op), ship-list-scoped patching with base-wins merge, and the full backup/mtime/tmp+rename/verify-or-restore ladder for ANY extension writing into another package's config. Adapt the install-layout probe and frontmatter grammar to your host. Omit pi-subagents path constants and the ACP tool names (data, not contract).