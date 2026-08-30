<!-- capsule-v2 -->
# Observability command trio — how does an extension expose its loaded cache without ever leaking it into the prompt?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must know what `/memory:status` and `/memory:list` actually report (and what they deliberately DON'T), why `agent_settled` is a registered no-op, and which cache states each command distinguishes — porting these as prompt-visible or auto-writing hooks breaks the human-curation boundary.

## Command surface (`agent_settled`, `/memory:status`, `/memory:list`)
**Path/Symbol:** `pi-memory.ts` agent_settled no-op (:288–289); `/memory:status` handler (:291–315); `/memory:list` handler (:351–368). All are `pi.on(...)`/`pi.registerCommand(...)` closures over the module-scoped `cache: MemoryCache | null`.
**Signature:** status/list: `async (_args, ctx) => void`; notify via `ctx.ui.notify(lines | summary, "info" | "warn")`.
**Data Shape:** status renders a multi-line block — roots (`cache.globalRoot`, `cache.workspaceRoot ?? "none"`), `Loaded files: N`, state line present-vs-`(empty)`, then one line per file; list renders ONE line `Global: X entries | Workspace: Y entries | Total: Z`.

### Decisive source
```ts
// ── agent_settled: No automatic writes ───────────────────────────
pi.on("agent_settled", async () => {});
...
for (const f of cache.files) {
  lines.push(`  [${f.source === "global" ? "G" : "W"}] ${f.relPath} (${f.injected.length}/${f.content.length} chars)`);
}
ctx.ui.notify(lines.join("\n"), "info");
```
```ts
if (!cache) { ctx.ui.notify("🧠 Pi Memory: not loaded", "warn"); return; }   // BOTH commands
const globalCount = cache.files.filter((f) => f.source === "global").length;
const wsCount = cache.files.filter((f) => f.source === "workspace").length;
```

**Flow:** every read command starts with the same guard — `cache === null` ⇒ warn "not loaded" and stop; otherwise derive counts/lines from the cached array only (NO re-read of the filesystem; disk truth requires `/memory:refresh`). Status prints per-file `[G]|[W]` tag + `injected/content` char pair so truncation is visible per file; list prints aggregate counts only.
**Invariant:** Both commands are READ-ONLY introspection of the in-memory cache: they never write files, never mutate `cache`, and never touch the system prompt — user-facing output goes through `ctx.ui.notify`, never through injection. The un-loaded (`null`) and loaded-but-empty (`files: []`) states are DISTINCT: null ⇒ "not loaded" warning; empty ⇒ zero counts with no error (and still no injection — see tiered-budget-overflow). The `[G]/[W]` tags mirror the same source field that drives merge precedence, so status makes layer collisions (`basename` overrides) visible as two separate lines. `agent_settled` is REGISTERED AND EMPTY on purpose: it documents "no automatic writes at turn end" (Pi's JSONL session already persists raw history) — deleting it or filling it with extraction logic silently converts the human-curated loop into an auto-memory product.

## Get live surrounding code
**Retrieve:** graph BM25 has NO Function node matching `"registerCommand notify"` (multi-word AND-semantics over closure tokens), so resolve by content search instead:
```bash
codebase-memory-mcp cli search_code '{"project":"pi-memory-extension","pattern":"registerCommand"}'
```
(Executed pass-3 audit at pin f3b4377f: single result `pi-memory` Module lines **292;318;352;371;481;533;585** — ALL SEVEN command registration sites, the observability pair among them.)

## Verdict
Adopt read-only, cache-backed introspection commands with an explicit not-loaded vs empty distinction and per-file truncation visibility. Keep a deliberate no-op turn-end hook as living documentation of the no-auto-write boundary. Adapt `ctx.ui.notify` to the host's UI channel; never route this output into prompts. Coverage caveat: no upstream suite — pinned by executed Node probe (P1a-c status-line contract incl. basename-collision coexistence, P2 count sum, P3 adversarial empty-cache ⇒ null-block + 0/0/0 counts, all GREEN at HEAD).
