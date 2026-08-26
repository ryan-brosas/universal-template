<!-- capsule-v2 -->
# UI/UX — transcript sanitization is a SECURITY surface, not cosmetics

**Source:** pi-fabric (monotykamary) MIT `<branch>@<commit>`; Codebase Memory `pi-fabric`. **Question:** how does every rendered foreign text (model/tool output) get made terminal-safe and secret-redacted without corrupting graphemes?

## Connected graph-selected seam
**Path/Symbol:** `src/ui/transcript-sanitization.ts`: `terminalSafe` (:15-23), `clip` (:37-45), `redactInlineSecrets` (:96-118), `redact` (:120-166); constants (:1-9: 500 summary / 160 encoded / 40k value / 12k string / 400 nodes).
**Signature:** `terminalSafe(text)` strips OSC…BEL/ST and CSI sequences, removes directional marks, maps C0/C1 controls to space, normalizes CR; `clip(text, budget)` clips by `Intl.Segmenter` graphemes keeping head ~75% + tail ~25% (max 1000) separated by `…\n`; `redact(text)` redacts by key-name regex then inline patterns.
**Data Shape:** output is arbitrary bytes from transcripts/tool args/model text; budgets bound per-field (500/160/40k/12k/400); recursion capped at depth 12 with node AND char budgets degrading gracefully (`[value omitted]`, `[N entries omitted]`).

### Decisive source
```ts
// OSC/CSI escapes can rewrite terminal state; Unicode BIDI marks can visually
// REORDER text to disguise commands; splitting graphemes corrupts emoji/CJK.
// strip OSC…BEL/ST and CSI sequences, remove directional marks (U+202A-E, U+2066-9, U+200E/F)
// clip by Intl.Segmenter GRAPHEMES keeping head ~75% + tail ~25% (max 1000) separated by "…\n"
// redact by KEY name regex (authorization|api[-_]?key|token|password|secret|cookie|credential|private[-_]?key)
//   then inline patterns (Bearer/Basic, sk-/pk-/ghp_/github_pat/xox…, auth headers, ENV=, --password=, user:pass@)
//   plus a charset+length heuristic flagging large base64-ish blobs
```

**Flow:** every value rendered from transcripts/tool args/model text passes `terminalSafe` (escape stripping, bidi defense) → `clip` (grapheme-safe, budgeted head/tail) → `redact` (layered secret redaction under budgets). Key-name redaction alone misses values embedded in strings, hence inline regexes. Recursion capped at depth 12 with node AND char budgets.
**Invariant:** one giant field can never starve all others (budgets); clipping never splits a grapheme; redaction degrades gracefully rather than truncating silently mid-structure.
**Probe:** `tests/fabric-ui.test.ts` (terminal-safe output survives OSC/CSI/bidi; clipped text keeps both ends visible; secret redaction catches embedded `sk-`/`Bearer` values).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "transcript sanitization terminalSafe redact clip bidi secret", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the layered sanitization (escape/bidi defense → grapheme-safe budgeted clip → layered secret redaction) with graceful degradation; adapt the budgets and regex set to host; omit the pi-fabric-specific widget/dashboard rendering unless the target has a TUI.

## Supporting UI patterns (porting checklist)
- **Word-diff emphasis** — confidence-gate any generated emphasis; drop rather than risk wrong highlights; noise-filter against opposite-side signal.
- **Spinner** — phase-lock animations to wall clock (`floor(now/250) % frames`); `.unref()` timers.
- **Hidden row borrowing** — measure freed rows and lend to neighbors; never let layouts jump.
- **Preview lines** — head/tail with explicit omitted-count markers; ring buffers when streaming.
- **Status widget** — glyph+color redundancy, activity-priority lines, row leasing, dismiss-until contracts, identity-keyed render caches.
