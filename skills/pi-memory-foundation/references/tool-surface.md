<!-- capsule-v2 -->
# Tool surface — the six memory tools + status doctor and the seven lifecycle hooks

**Source:** pi-memory (MIT, `main@39e6b998a2279c8fad4a2c6c64e26828c1d6023e`); Codebase Memory `pi-memory`. **Question:** How does an agent wire the memory primitives into a coding-agent extension — registering the tools and lifecycle hooks that make memory write/read/forget/restore/search/status usable every turn?

## Tool surface
**Path/Symbol:** `index.ts` default export (1426–2431): `pi.on("session_start")` (1428–1462), `pi.on("session_shutdown")` (1465–1529), `pi.on("input")` (1532–1537), `pi.on("before_agent_start")` (1540–1584), `pi.on("session_before_compact")` (1587–1632), `pi.registerTool("memory_write")` (1635–1753), `pi.registerTool("scratchpad")` (1756–1931), `pi.registerTool("memory_read")` (1934–2043), `pi.registerTool("memory_forget")` (2046–2150), `pi.registerTool("memory_restore")` (2153–2213), `pi.registerTool("memory_search")` (2216–2348), `pi.registerTool("memory_status")` (2351–2430).
**Signature:** `export default function (pi: ExtensionAPI): void`.
**Data Shape:** 6 tools (memory_write, scratchpad, memory_read, memory_forget, memory_restore, memory_search) + memory_status doctor; 7 hooks (session_start, session_shutdown, input, before_agent_start, session_before_compact). Tool params use `@earendil-works/pi-ai` `Type.Object`/`StringEnum`/`Type.Optional`. Every write path calls `ensureDirs()` then `ensureQmdAvailableForUpdate()` + `scheduleQmdUpdate()`.

### Decisive source
```ts
// memory_write long_term append (1734-1739): stamp + append + schedule qmd
const separator = existing.trim() ? "\n\n" : "";
const stamped = `<!-- ${ts} [${sid}] -->\n${content}`;
fs.writeFileSync(MEMORY_FILE, existing + separator + stamped, "utf-8");
await ensureQmdAvailableForUpdate();
scheduleQmdUpdate();

// memory_forget (2105-2116): write the recovery record BEFORE mutating the file
const result = forgetBlocks(existing, params.match);
const recovery = writeRecoveryRecord(target, recoveryDate, result.removed);
fs.writeFileSync(filePath, result.content, "utf-8");
snapshotDirty = true;

// before_agent_start (1567-1583): inject the memory block into the system prompt
return { systemPrompt: event.systemPrompt + headerLines.join("\n") };
```

**Flow:** (1) `session_start` detects qmd, auto-sets-up the collection, runs a catch-up embed, and refreshes the snapshot. (2) `before_agent_start` injects the memory context (stable snapshot or per-turn rebuild) into the system prompt with usage instructions. (3) The tools implement the write/scratchpad/read/forget/restore/search/status contracts, each stamping entries with `<!-- ts [sid] -->` and scheduling a qmd update. (4) `session_shutdown` writes a gated exit summary; `session_before_compact` writes a HANDOFF block and refreshes the snapshot.

**Invariant:** every memory mutation is stamped with a timestamp+session comment, schedules a qmd update, and (for long-term/forget/restore) marks the snapshot dirty; deletion persists a recovery record before mutating; the memory block is injected before every agent turn.

**Probe:** `test/unit.test.ts` — `extension registration` describe (:2007): `registers all 7 tools` (:2008), `registers all 4 lifecycle hooks` (:2021), `tools have labels and descriptions` (:2030); `lifecycle hooks` describe (:1352): `registers all expected hooks` (:1367), `before_agent_start returns undefined when no memory files` (:1376), `before_agent_start injects memory into system prompt` (:1382); `memory_write tool` (:771), `scratchpad tool` (:904), `memory_read tool` (:1055), `memory_forget tool` (:2275), `memory_search tool` (:1263), `memory_status tool` (:1308) describes. Coverage caveat: `test/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-memory", query: "registerTool memory_write memory_forget memory_restore memory_search memory_status", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tool/hook surface, the stamp-then-schedule write pattern, the recovery-before-mutation forget, and the before-every-turn injection. Adapt the tool names, the `pi` ExtensionAPI integration, and the prompt wording to the host. Omit the Pi-specific `pi.on`/`pi.registerTool`/`ctx.ui` wiring unless a target uses the same extension API.
