<!-- capsule-v2 -->
# Pi-settings mirror — global+project deepMerge with back-compat key ladders

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter read pi settings it doesn't own (enableSkillCommands, quietStartup) without breaking on pi's global/project layering or renamed keys?

## Settings merge
**Path/Symbol:** `src/acp/pi-settings.ts` whole file (75L): `deepMerge` (:9-17), `readJsonFile` (:19-28), `getMergedSettings` (:30-37), `getAgentDir` (:39-41), `getEnableSkillCommands` (:47-58), `getQuietStartup` (:64-75).
**Signature:** `getEnableSkillCommands(cwd: string): boolean`; `getQuietStartup(cwd: string): boolean`.
**Data Shape:** merged `Record<string, unknown>` from `<agentDir>/settings.json` (global) then `<cwd>/.pi/settings.json` (project). `getAgentDir()` honors `PI_CODING_AGENT_DIR` env override (`resolve()`d), defaulting to `~/.pi/agent`.

### Decisive source
```ts
function deepMerge(a, b) {
  const out = { ...a }
  for (const [k, v] of Object.entries(b)) {
    const av = out[k]
    if (isObject(av) && isObject(v)) out[k] = deepMerge(av, v)   // arrays are REPLACED not concatenated
    else out[k] = v                                              // project value wins on any type mismatch
  }
  return out
}
export function getQuietStartup(cwd: string): boolean {
  const merged = getMergedSettings(cwd)
  const direct = merged.quietStartup
  if (typeof direct === 'boolean') return direct
  const legacy = (merged as any).quietStart      // back-compat: some versions used quietStart
  if (typeof legacy === 'boolean') return legacy
  return false                                    // quietStartup defaults FALSE (verbose prelude shown)
}
```

**Flow:** every consumer call re-reads BOTH files from disk (no cache — settings edits apply to the next session without restart). `readJsonFile` returns `{}` for missing/unparsable/non-object roots, so a corrupt project file degrades to global-only instead of failing the session. `getEnableSkillCommands` ladder: direct boolean → nested `skills.enableSkillCommands` → default TRUE (skill commands ON). Consumers: `newSession`/`loadSession` pass it into `toAvailableCommandsFromPiGetCommands`; `getQuietStartup` gates the startup-info prelude (see below).

**Invariant:** project overrides global per-key via recursive merge ONLY where both sides are plain objects — an array or scalar on either side replaces wholesale (a porter who concatenates arrays or shallow-merges changes semantics). Every getter must end in a typed default (`true` for skills, `false` for quietStartup) and never throw; unknown/renamed keys resolve through explicit back-compat aliases, not schema validation. quietStartup=TRUE suppresses the verbose prelude BUT the update notice still ships alone (agent.ts :452-470: `preludeText = updateNotice ? updateNotice + '\n' : ''`), and on session RESTORE bridge diagnostics override quiet mode (agent.ts :1164-1173: restored bridge info still emits when `diagnostics.length || failed || !catalogComplete || lifecycle !== 'ready'`).

**Probe:** `test/unit/startup-info-env.test.ts` / `test/unit/new-session-runtime-startup-errors.test.ts` exercise the cwd/env plumbing around these getters (no dedicated unit test for pi-settings.ts itself at this pin — source-read verified; keep the caveat when porting).
**Coverage:** check_index_coverage `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "getMergedSettings deepMerge enableSkillCommands quietStartup", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-file deepMerge with object-vs-object recursion, `{}`-on-corruption reads, and typed back-compat ladders ending in explicit defaults. Adapt `PI_CODING_AGENT_DIR` and the `.pi/settings.json` layout to your host's naming. Omit nothing — the file is small enough to port whole.
