<!-- capsule-v2 -->
# Memorable name generator & color hashing — how do agents get stable, collision-resistant identities and colors?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** How are agent names minted across themes, validated, and mapped to consistent ANSI colors?

## Theme word lists → AdjNoun; name-hash → 8-color palette
**Path/Symbol:** `lib/names.ts:generateMemorableName` (:174-206), `isValidAgentName` (:208-211), `agentColorCode` (:213-222), word tables (:14-170).
**Signature:** `generateMemorableName(themeConfig?: NameThemeConfig): string`; `agentColorCode(name): string` (ANSI 38;2 truecolor sequences).
**Data Shape:** themes: default (24×24), nature/space (16×16), minimal (single Greek list), custom (`themeConfig.customWords` with DEFAULT fallbacks PER LIST).

### Decisive source
```ts
case 'custom':
  adjectives = themeConfig?.customWords?.adjectives ?? DEFAULT_ADJECTIVES;
  nouns = themeConfig?.customWords?.nouns ?? DEFAULT_NOUNS;   // per-list fallback, not all-or-nothing
...
let hash = 0;
for (const char of name) hash = (hash << 5) - hash + char.charCodeAt(0);
const color = AGENT_COLORS[Math.abs(hash) % AGENT_COLORS.length];   // JS 32-bit overflow dance
```
Validation: `/^[a-zA-Z0-9_][a-zA-Z0-9_-]*$/`, max length 50.

**Flow:** names are random draws (collision handling lives in findAvailableName/allocateSessionChannelId, NOT here); the hash is the classic `(h<<5)-h+c` Java-string hash with `Math.abs` before modulo because JS bitwise ops can go negative; results memoized in a Map so a name's color never changes within a process.
**Invariant:** Color stability is per-process only — two sessions may render the same name differently after restart; nothing persists it. The custom-theme fallback is per-list: supplying only adjectives keeps default nouns.
**Probe:** direct tests via registration suites exercising name generation (`tests/channel.test.ts::creates phrase-based session channels...` pins kebab phrase grammar for channels; agent-name validation exercised through register paths); `grep -c "Math.abs(hash)" lib/names.ts` (=1); `grep -c "'minimal'" lib/names.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "generateMemorableName agentColorCode isValidAgentName NameThemeConfig", limit: 5 });
```

## Verdict
Adopt theme-table name minting + 32-bit hash color assignment + the validation regex; adapt palettes/lists; add persistence if you need cross-restart color identity.
