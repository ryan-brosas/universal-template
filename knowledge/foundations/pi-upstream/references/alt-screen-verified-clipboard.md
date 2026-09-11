<!-- capsule-v2 -->
# Verified clipboard handoff — why does an alt-screen copy report failure even after writing OSC 52?

**Source:** pi-upstream MIT `main@a470b121bf683b4c2b9fc0b3a7c807de7e0cfe9c` (introduced by drift commit `a69bef789`-era selection work; file changed `534bcbff..a470b121`). Codebase Memory `pi-upstream`. **Question:** A porter wires terminal selection-copy to an OSC 52 escape write and flashes "Copied!" — when does that lie to the user, and what is the injection contract?

## copySelection option + async copySelectionToClipboard
**Path/Symbol:** `packages/tui/src/tui-alt-screen.ts:153-158` (`TuiAltScreenOptions.copySelection`), `:1082-1092` (decision comment + dispatch in `copySelectionToClipboard`, now `async`), call site `:984` (`void this.copySelectionToClipboard()`).
**Signature:** `copySelection?: (text: string) => Promise<boolean>` — resolve `true` only on verified success; the component falls back to a bare OSC 52 write and still reports success when the option is absent.
**Data Shape:** Selection bounds → text extracted from `previousScreen`/viewport lines joined with `\n`; empty extraction returns silently before any copy attempt.

### Decisive source
```ts
// Prefer an injected clipboard implementation (native clipboard + platform tools with a
// verified success path) when the host app provides one. A bare OSC 52 write can show
// "Copied!" while leaving the system clipboard untouched (e.g. macOS Terminal.app, tmux
// without OSC 52 clipboard passthrough), so only report success when it actually copies.
```

**Flow:** mouse-selection release → `handleSelectionMouseEvent` accepts button 0 during drag AND release events carrying button bits `& 3 === 3` (:955-957 — release frames encode no primary button) → bounds computed → `void this.copySelectionToClipboard()` (fire-and-forget promise; render not blocked on clipboard I/O) → if host provided `copySelection`, await its boolean; success = flash confirmation, otherwise error flash; without the option, fall back to OSC 52 write.
**Invariant:** Never claim copy success from "bytes written to stdout" — OSC 52 is best-effort transport that several mainstream terminals silently drop (macOS Terminal.app, tmux without passthrough); verification requires the platform tool's own exit status. Related drift seam: viewport input defers to focused overlays via `shouldDeferViewportInputToOverlay()` (:535-537, checked before wheel routing :563 and keybinding matching :597) so search-overlay typing never scrolls the page underneath.
**Probe:** `packages/tui/test/` — alt-screen suite exercises selection handling at this pin; deterministic source probes: `grep -n "only report success when it actually copies" packages/tui/src/tui-alt-screen.ts` (1 hit at :1091 comment block) and `grep -n "shouldDeferViewportInputToOverlay" packages/tui/src/tui-alt-screen.ts` (≥3 hits: definition + two call sites). Coverage caveat: upstream test coverage for the injected-copy success/failure branches was not located at this pin — treat the comment as contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "copySelection clipboard selection osc 52", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the injection contract: optional host-provided `copySelection(text): Promise<boolean>` preferred over raw OSC 52, success flashed only on verified copy, copy awaited fire-and-forget so rendering never blocks. Adapt the platform-tool set behind the boolean. Omit the overlay-deferral rule only if your TUI has no focusable overlays. Coverage caveat: behavior branch tests not located upstream at this pin; pinned by source citation + deterministic greps.
