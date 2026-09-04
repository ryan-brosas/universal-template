<!-- capsule-v2 -->
# Thinking-level plumbing — how does one 7-value effort enum stay valid end-to-end across config validation, actor templates, and two different CLI dialects?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** where is the canonical thinking level defined, how does it flow (default → config → request → runner argv), and what must a porter NOT translate?

## One ordered enum, validated at every boundary, translated only at the CLI edge
**Path/Symbol:** `src/thinking.ts` whole (:1-41) — `FabricThinking = "off"|"minimal"|"low"|"medium"|"high"|"xhigh"|"max"`, `DEFAULT_FABRIC_THINKING = "medium"` (:13), `THINKING_LEVELS` (:16-24), `isFabricThinking` (:27-28), `thinkingLabel` (:41). Translation: `src/agents/claude-cli.ts:claudeEffort` (:123-124) + `buildClaudeArguments` :146. Resolution: `src/agents/manager.ts:575` (`const thinking = request.thinking ?? this.config.thinking;`). Config gate: `src/config.ts` `thinkingValue` (:474-475), agents default :285, prewalk :581-589. Worker passthrough: `src/worker.ts:296` (`--thinking`). Template storage: `src/actors/global-registry.ts:259-260,340-342`. Direct tests `tests/agent-manager.test.ts` (:674-719 default/override/medium pins; :1010→1025 claude argv pin) and `tests/config.test.ts:144-157`.
**Signature:** `claudeEffort(thinking: FabricThinking): string`; `isFabricThinking(value): value is FabricThinking`.
**Data Shape:** ordered lowest→highest matching pi-ai's EXTENDED_THINKING_LEVELS; Pi receives the raw level via `--thinking <level>` and clamps to model-supported levels itself with next-highest fallback (pi-ai `clampThinkingLevel`); Claude receives `--effort`.

### Decisive source
```ts
// thinking.ts header comment — THE contract:
// Fabric resolves a thinking level per run (explicit call/actor value, else the
// Fabric default "medium"). Pi receives it via "--thinking" and clamps it to
// the model's supported levels using next-highest fallback. Claude receives it
// via "--effort"; off/minimal map to low.
export const claudeEffort = (thinking: FabricThinking): string =>
  thinking === "off" || thinking === "minimal" ? "low" : thinking;

// manager.ts :575 — single resolution point, precedence call > config:
const thinking = request.thinking ?? this.config.thinking;

// global-registry.ts :259 — template values re-validated per-field, never trusted:
const thinking = def.thinking !== undefined && isFabricThinking(def.thinking)
  ? def.thinking : undefined;
```

**Flow:** config normalization validates via `isFabricThinking` and falls back to defaults (`thinkingValue`) → actor templates store only valid levels on create AND on load from disk (:340-342 filters persisted records field-by-field) → per-run resolution picks `request.thinking ?? config.thinking` in AgentManager → worker passes `--thinking <level>` to the pi binary verbatim while the claude adapter maps off/minimal→low for its `--effort` flag. Fabric NEVER clamps to a model's supported set — that is the pi-ai runtime's job at execution time.
**Invariant:** the enum is the ONLY interchange unit — do not invent intermediate levels or clamp in Fabric; the Claude dialect mapping is total (no "off" ever reaches `--effort`); an invalid stored template value silently drops to `undefined` (inherit run default) rather than failing the load.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "off/minimal map to" src/thinking.ts'` → line 7; `grep -n "const thinking = request.thinking ?? this.config.thinking" src/agents/manager.ts` → line 575; tests pin all three legs: default-forward :686 `expect(result.thinking).toBe("high")`, medium fallback :719 `expect(result.thinking).toBe("medium")`, claude argv `thinking: "minimal"` → `"--effort", "low"` :1010-1025, config drop of invalid `normalizeFabricConfig({prewalk:{thinking:"extreme"}})` :152.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "claudeEffort thinking level effort argument", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `claudeEffort` src/agents/claude-cli.ts 123-124.)

## Verdict
Adopt the single-source enum with per-boundary type-guard validation and translation-only-at-the-executor-edge layering for any multi-runner effort/thinking surface; adapt flag names to your CLIs; omit the label table if you have no picker UI. All legs direct-tested — no coverage caveat.
