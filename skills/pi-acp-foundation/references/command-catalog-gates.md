<!-- capsule-v2 -->
# Command catalog filtering — extension/skill visibility gates + describe fallback

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How do you turn pi's raw get-commands payload into the ACP available-commands list, deciding which sources/skills the client may see and what description a command with none gets?

## Catalog filter
**Path/Symbol:** `src/acp/pi-commands.ts` whole file (59L): `PiRpcCommandInfo` (:3-9), `describeFallback` (:11-20), `toAvailableCommandsFromPiGetCommands` (:22-59).
**Signature:** `toAvailableCommandsFromPiGetCommands(data: unknown, opts?: {enableSkillCommands?: boolean; includeExtensionCommands?: boolean}): {commands: AvailableCommand[]; raw: PiRpcCommandInfo[]}`.

### Decisive source
```ts
const commandsRaw = Array.isArray(root?.commands) ? root.commands
                  : Array.isArray(root?.data?.commands) ? root.data.commands : []   // tolerate both envelopes
for (const c of commandsRaw) {
  const name = typeof c?.name === 'string' ? c.name.trim() : ''
  if (!name) continue                                            // nameless entries silently dropped
  const source = typeof c?.source === 'string' ? c.source : ''
  if (!includeExtensionCommands && source === 'extension') continue  // DEFAULT: hide extension commands
  if (!enableSkillCommands && name.startsWith('skill:')) continue    // opt-out kills the skill: NAMESPACE
  out.push({ name, description: desc || describeFallback(c) })
}
// describeFallback: `(source:location)` from whatever string fields exist, else '(command)'
```

**Flow:** defaults are `enableSkillCommands: true`, `includeExtensionCommands: false` — extension commands (which would double-expose tools the MCP bridge already surfaces as `ide_*`) stay hidden unless explicitly opted in; skill commands are visible by default and gated TOGETHER by the single settings flag (`getEnableSkillCommands`), keyed on the `skill:` NAME PREFIX rather than a source tag. Both the filtered list AND the raw payload are returned so callers can re-filter with different options without a second RPC. The dual-envelope probe (`root.commands` / `root.data.commands`) absorbs pi RPC response-shape drift.

**Invariant:** filtering is by source string for extensions but by NAME PREFIX for skills — a porter who filters skills by source too loses every skill when pi doesn't set that source. An empty description must never ship empty: fall back to `(source:location)` or `(command)` because ACP clients render the description as the only context in their slash menu.

**Probe:** `test/unit/pi-commands.test.ts` — "hides extension commands by default and filters skill commands" (:5) pins all three modes (default / includeExt / noSkills); `test/unit/builtin-commands.test.ts` pins the builtin-command surface end-to-end.
**Coverage:** check_index_coverage `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "toAvailableCommandsFromPiGetCommands enableSkillCommands includeExtensionCommands", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the default-hidden extension gate, prefix-keyed skill gate, dual-envelope tolerance, and describe-fallback chain returning `{commands, raw}`. Adapt source names/prefixes to your agent's taxonomy. Omit nothing.
