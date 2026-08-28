<!-- capsule-v2 -->
# Config registration pipeline — how does static config (JSON documents + markdown globs) become live agent/command/skill rows with correct precedence over built-ins?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A host loads user configuration from JSON documents and markdown file globs and must turn it into live agent/command/skill/reference rows WITHOUT letting a malformed file break boot, while keeping config strictly more powerful than built-in registrations. How is that pipeline ordered, and what exactly wins when both sides define the same row?

## Draft-update ordering over silent-skip decoding
**Path/Symbol:** `packages/core/src/config/plugin/command.ts` (`Plugin.effect` :21-52, `loadDirectory` :55-71, `decode` :73-83), `packages/core/src/config/plugin/agent.ts` (`Plugin.effect` :53-127, `discover` :164-177, `decode` :179-211, `expandPermissions` :133-140, `expandHome` :142-153), `packages/core/src/config/plugin/skill.ts` (`Plugin.effect` :16-49), `packages/core/src/config/plugin/provider.ts` (integration transform :21-44, catalog transform :46-112), `packages/core/src/config/plugin/reference.ts` (`validAlias` :62-64, `local` :66-72, `localPath` :74-78).
**Signature:** `Plugin = define({ id, effect: (ctx) → Effect<void> })`; each writes via `ctx.<domain>.transform((draft) => ...)`; `draft.update(id, fn)` merges, `draft.remove(id)` deletes, `draft.source(...)`/`draft.add(...)` append.
**Data Shape:** `Config.Entry = Document{path, info} | Directory{path}`; markdown files decode to `{name, info}` where name is the relative path minus the `command(s)/`/`agent(s)/`/`mode(s)/` prefix and `.md` suffix.

### Decisive source
```ts
// config/plugin/agent.ts:53-79 — global permissions pushed onto EVERY agent BEFORE per-agent ones;
// disabled: true REMOVES the row (how a built-in is disabled)
const permissions = expandPermissions(
  documents.flatMap((document) => document.info.permissions ?? []),
  global.home,
)
if (configuredDefault !== undefined) draft.default(AgentV2.ID.make(configuredDefault))
for (const current of draft.list()) {
  draft.update(current.id, (agent) => agent.permissions.push(...permissions))
}
for (const [id, item] of Object.entries(document.info.agents ?? {})) {
  const agentID = AgentV2.ID.make(id)
  if (item.disabled) { draft.remove(agentID); continue }
  ...
}
```

**Flow:** Config plugins run AFTER built-ins in the fixed State.batch order (pass-14 capsule), so any `draft.update` on the same ID lands on top of the built-in row — config beats built-ins by draft-update order, not by a precedence flag. Each plugin iterates `config.entries()`: documents contribute inline maps (`info.commands`, `info.agents`, `info.providers`, `info.skills`, `info.references`); directories contribute glob-discovered markdown files (`{command,commands}/**/*.md`, `{agent,agents}/**/*.md` + `{mode,modes}/*.md` with `primary: true` forcing `mode: "primary"`), sorted, dot+symlink aware, glob failures swallowed to `[]`. Markdown decode is fail-soft: `ConfigMarkdown.parseOption` returns undefined on bad frontmatter, Schema decode is `decodeUnknownOption`, and undefined results are filtered out — a malformed file is silently skipped, never fatal. Agent markdown with frontmatter keys OUTSIDE the known `agentKeys` set takes the V1 decode path (`ConfigAgentV1.Info` + `ConfigMigrateV1.migrateAgent`), so legacy keys like `temperature:` and `tools:` migrate transparently (temperature becomes `request.body.temperature`). Model strings parse through `ModelV2.parse` and re-pin `{id, providerID}` while PRESERVING the existing variant (`item.model?.variant`); a separate `variant` field then overrides it. Provider rows merge headers/body via `Object.assign` so later documents layer ON TOP; model variants MERGE by id (find existing, assign headers/body) so config never wipes models.dev variants; cost normalizes to the tiered array with cache defaults 0; `disabled` flips `enabled`. Skill config registers SOURCES, not files: per directory both `<dir>/skill` and `<dir>/skills` DirectorySources; per `skills` item an http(s) URL becomes a UrlSource, `~/` expands to global home, relative joins `location.directory`. Reference aliases must be non-empty with no `/`, whitespace, backtick, or comma; string entries starting `.`/`/`/`~` are local paths (resolved against the document directory), objects with `repository` become GitSources.
**Invariant:** config always beats built-ins (batch order); a malformed file never blocks boot (fail-soft decode); global config permissions apply before per-agent permissions; `disabled: true` removes even built-in agents; `~`/`$HOME` expansion happens ONLY for path-actions (external_directory/read/edit) — bash resources stay raw shell text because safe expansion needs shell-aware parsing (inline comment pins this).
**Probe:** `packages/core/test/config/agent.test.ts` (349L, 5 `it.effect` + 1 `it.live`): "applies all global permissions before agent-specific permissions" pins the exact permission array order and `removed` agent deletion; "loads legacy file-based agents from config directories" pins V1 migration (`temperature: 0.5` → `request.body.temperature`) and `modes/plan.md` → primary mode. `packages/core/test/config/command.test.ts` (83L, 1 `it.live`): pins the full ordered command list from inline + file sources including `nested/docs` naming and empty-template commands. `packages/core/test/config/skill.test.ts` (80L, 1 `it.effect`): pins the exact source list (both directory spellings, relative/~/absolute/URL expansion). `packages/core/test/config/provider.test.ts` (269L, 3 `it.effect`): pins three-document layering (variant header merge `{first, shared:last, last}`, default-model last-wins, env-method registration). Source pin:
```bash
grep -c 'draft.update' packages/core/src/config/plugin/command.ts   # expect 1
grep -c 'draft.remove' packages/core/src/config/plugin/agent.ts    # expect 1
grep -c 'ConfigMigrateV1' packages/core/src/config/plugin/agent.ts # expect 2
grep -c 'it.effect' packages/core/test/config/agent.test.ts        # expect 5
grep -c 'it.live'   packages/core/test/config/command.test.ts      # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ConfigAgentPlugin expandPermissions draft.remove disabled legacySources ConfigMigrateV1 ConfigCommandPlugin loadDirectory ConfigSkillPlugin DirectorySource UrlSource ConfigProviderPlugin configuredIntegrations variant merge", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt draft-update ordering as the precedence mechanism, fail-soft markdown decoding with silent skip, the global-before-agent permission push, `disabled`-removes semantics, variant-preserving model parsing, and path-action-only home expansion. Adapt the config entry/document schema and the glob patterns to the host's layout. Omit the V1 migration ladder if the host has no legacy format (but keep the fail-soft skip). Coverage caveat: the `mode(s)/*.md` primary-forcing path is pinned only indirectly through the legacy test; the reference plugin has no dedicated test file (source-confirmed only); Codebase Memory MCP not connected this session, Retrieve marked for re-execution on graph reconnect; bun runner blocked at this checkout, probes are byte-exact greps.
