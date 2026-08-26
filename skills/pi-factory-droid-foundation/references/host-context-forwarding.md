<!-- capsule-v2 -->
# Host-context forwarding — how does host persona/memory/skills context ride into a bridged external agent?

**Source:** pi-factory-droid MIT `master@e0a53248ab173b6f0ff763441c1f1160bedd016e`; Codebase Memory `pi-factory-droid`. **Question:** The bridged agent keeps its own harness prompt and tools — how do I make it still know who it is (persona), what it remembers (AGENTS.md), and which skills exist, without leaking host internals or breaking turns when discovery fails?

## Context block + one-shot preamble prepend
**Path/Symbol:** `src/providers.ts:buildContextBlock` (367-389), `agentsSkillDirs` (393-405), `renderPreamble` (407-417); consumption in `streamDroidPiTools` 501-506 / `streamDroidAgent` 596-601 via `entry.pendingPreamble`.
**Signature:** `function buildContextBlock(cwd: string, cfg: ResolvedConfig): string`; `function renderPreamble(contextBlock: string): string`
**Data Shape:** block = trimmed AGENTS.md content joined with `\n\n` to a formatted skills catalog; preamble wraps the block in `<host-context>...</host-context>` between bridge-explanation lines; stored per pool entry as `pendingPreamble: string | null`.

### Decisive source
```ts
if (!cfg.forwardContext) return "";
const parts: string[] = [];
const agents = readMaybe(join(cwd, "AGENTS.md"));
if (agents?.trim()) parts.push(agents.trim());
try {
  const { skills } = loadSkills({
    cwd,
    agentDir: join(homedir(), ".pi", "agent"),
    // Pi's `.agents/skills` tiers (cwd ancestors + ~/.agents) are discovered
    // by its package-manager layer, NOT by core loadSkills — walk them
    // ourselves, closest first so name collisions resolve member > tenant >
    // global, matching Pi's own precedence.
    skillPaths: agentsSkillDirs(cwd),
    includeDefaults: true,
  });
  ...
} catch {
  // Skills are additive context; a scan failure must not break the turn.
}
return parts.join("\n\n");
```

Tier walk and one-shot delivery:
```ts
let dir = cwd;
for (let depth = 0; depth < 32; depth++) {
  dirs.push(join(dir, ".agents", "skills"));
  if (existsSync(join(dir, ".git"))) break;   // stop at git root
  const parent = dirname(dir);
  if (parent === dir) break;                  // fs root
  dir = parent;
}
dirs.push(join(homedir(), ".agents", "skills"));   // then user-global
return dirs.filter((candidate) => existsSync(candidate));
```
```ts
const turn = extractLatestTurn(context);
let turnText = turn.text;
if (entry.pendingPreamble) {
  turnText = `${entry.pendingPreamble}\n\n${turnText}`;
  entry.pendingPreamble = null;      // FIRST turn after (re)creation only
}
```

**Flow:** buildContextBlock runs per TURN (hosts regenerate AGENTS.md) → its sha256 is the pool entry's `contextHash`, so an edit recreates the Droid session → on creation the block is rendered once into `pendingPreamble` → prepended to the first turn text, then cleared. Skills are presented as file paths — the bridged agent reads SKILL.md with its own tools.
**Invariant:** Context forwarding must be all-or-nothing per config flag (`forwardContext=false` ⇒ empty block ⇒ no preamble); skill-scan failure must degrade to AGENTS.md-only context, never fail the turn; the preamble is delivered EXACTLY once per session lifetime (cleared on use), and only a context-hash change may re-deliver it.
**Probe:** `test/context-forward.test.ts:23-40` ("forwards AGENTS.md and cwd-local skills" — temp cwd with Chinese persona text + `.agents/skills/ctx-probe/SKILL.md`, both matched in output); `:42-50` (forwardContext=false ⇒ ""); `:52-57` (renderPreamble emits `<host-context>\nBLOCK\n</host-context>`, mentions SKILL.md usage). Runner caveat: suite blocked in this checkout (tsx absent); assertions read and pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-factory-droid", query: "buildContextBlock renderPreamble agentsSkillDirs pendingPreamble", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt: context-as-user-message (never system-prompt injection), tiered closest-first skill-dir walk bounded at the git root with a user-global tail, fail-open scanning, hash-gated recreation, and exactly-once preamble delivery. Adapt what counts as "persona/memory" files and the preamble copy for your locale/host. Omit Pi's loadSkills defaults plumbing.
