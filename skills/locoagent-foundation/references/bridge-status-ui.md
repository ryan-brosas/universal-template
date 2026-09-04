<!-- capsule-v2 -->
# Bridge status UI — ANSI row accounting and the render-guard state machine

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does a non-React CLI keep a live status block at the terminal bottom without corrupting rows or erasing error states?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeUI.ts` — `countVisualLines` (:95-115), `clearStatusLines` (:124-131, `\x1b[N A` + `\x1b[J`), `printLog` clear-then-write (:134-137), state machine fields (:52-88), `renderStatusLine` early-return guard (:188-194), `setSessionTitle`/`refreshDisplay` reconnecting-failed guards (:504-528), worktree branch-hiding (:218-222); pure helpers in `src/bridge/bridgeStatusUtil.ts` (`computeShimmerSegments` grapheme split :79-111, OSC-8 zero-width links :161-163, `getBridgeStatus` :124-141).
**Signature:** `createBridgeLogger({verbose, write?}) → BridgeLogger` (26-method surface from types.ts:213-262; headless twin `createHeadlessBridgeLogger` maps every method to a line-log fn or noop).
**Data Shape:** `statusLineCount` tracks VISUAL rows (wrap-aware), not logical lines.

### Decisive source
```ts
// The trailing \n in "line\n" produces an empty last element — don't count it
// because the cursor sits at the start of the next line, not a new visual row.
if (text.endsWith('\n')) { count-- }
...
// Guard against reconnecting/failed — renderStatusLine clears then returns
// early for those states, which would erase the spinner/error.
if (currentState === 'reconnecting' || currentState === 'failed') return
```

**Flow:** write status → remember its visual height → next update: cursor-up N rows, erase-to-end, redraw. Permanent logs interleave by clearing first, writing, then letting the next tick redraw. State machine: idle → attached → titled, with reconnecting/failed as RENDER-FROZEN states (updates mutate data but skip render so the spinner/error survives). Multi-session adds a capacity line + per-session bullet list keyed by COMPAT session IDs with OSC-8 hyperlinked titles (zero visual width, so strip-ansi-based counting stays correct). Shimmer animation segments text by GRAPHEME + display width, not string indices — CJK/emoji safe.

**Invariant:** (1) Row accounting must match what the terminal actually rendered: wrap-aware widths, trailing-newline discount, zero-width escape sequences. Off-by-one here smears garbage up the screen. (2) States that own the full frame (reconnecting, failed) must refuse re-renders triggered by data-only updates. (3) In worktree mode hide the bridge's own branch — each session has its own, so it misleads. (4) The headless logger proves the surface is fully injectable: same interface, zero terminal writes.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "not a new visual row" src/bridge/bridgeUI.ts` (:109-110); `grep -n "would erase the spinner" src/bridge/bridgeUI.ts` (:508-509 and :524-525); `grep -n "misleading" src/bridge/bridgeUI.ts` (:217-219); graph resolves `locoagent.src.bridge.bridgeUI.createBridgeLogger` :42-530 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createBridgeLogger countVisualLines clearStatusLines renderStatusLine computeShimmerSegments", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the row-accounting + render-guard scheme for any raw-terminal live display; adopt the noop-logger twin as the template for headless embedding. Adapt colors/frames freely — the invariants are in the accounting, not the aesthetics.
