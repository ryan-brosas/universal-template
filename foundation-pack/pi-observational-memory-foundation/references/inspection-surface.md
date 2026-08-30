<!-- capsule-v2 -->
# Inspection surface — projection drift reporting (/om:status), content-only view + clipboard ladder (/om:view)

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** How do you make a hidden compaction pipeline trustworthy — showing users what is remembered, what will fire next, and whether the visible snapshot has drifted?

## Status command (`src/commands/status.ts`)
**Path/Symbol:** `status.ts:41-111` (`registerStatusCommand`), `status.ts:14-37` (`appendSuffixes`, drift suffixes).
**Signature:** `pi.registerCommand("om:status", …)` → single `ctx.ui.notify(lines.join("\n"), "info")`.
**Data Shape:** sections `── Mode ── / ── Memory ── / ── Activity ── / ── In flight ── / ── Last error ──`; observation line = `recorded / dropped / active / visible` counts plus optional `+N -N` drift suffixes.

### Decisive source
```ts
const folded = foldLedger(entries);
const visible = visibleProjection(entries);   // latest om.folded details snapshot
const full = fullProjection(entries);         // replay of ALL recorded custom entries
const drift = diffProjection(visible, full);

const observationLine = appendSuffixes(
	`Observations: ${folded.observations.length} recorded / ${folded.droppedObservationIds.size} dropped /`
	+ ` ${folded.activeObservations.length} active / ${visible.observations.length} visible`,
	[addedSuffix(drift.observationsOnlyInFull.length),   // recorded but not yet compacted-visible
	 removedSuffix(drift.droppedOnlyInFull.length)],     // still visible but already dropped
);
```

**Flow:** four independent progress meters (`rawTokensSinceObservationCoverage`, `…ReflectionCoverage`, `rawTokensSinceLastCompaction` vs `resolveCompactAfterTokens`) render as `~X / Y tokens (P%)`; the ACTIVE pool line deliberately re-renders with `observationPoolMetrics` (full rendered-line budget) while the VISIBLE pool uses stored `tokenCount`s; passive mode prepends a mode section instead of hiding data; in-flight and per-stage last errors come off the Runtime singleton.
**Invariant:** Drift suffixes are the honesty mechanism: between compactions, `visible` (the frozen `om.folded` snapshot) necessarily lags `full` (ledger truth) — surfacing `+1 -1` makes the lag measurable instead of silent, and tests pin that NO legacy "committed/pending" vocabulary may return. The two pool lines intentionally DISAGREE by design (stored tokenCount vs re-rendered line cost); the status text labels them separately so the discrepancy reads as information.

## View command + clipboard ladder (`src/commands/view.ts`, `src/clipboard.ts`)
**Path/Symbol:** `view.ts:47-79` (`registerViewCommand` handler), `view.ts:11-17` (`firstArg` tri-modal parse), `clipboard.ts:10-24` (`getClipboardCommands`), `clipboard.ts:26-35` (`copyTextToClipboard`).
**Signature:** `/om:view [full|visible]` → renders `renderContentOnlyProjection(projection, emptyScope)` then appends copy result.
**Data Shape:** output = content body + `\n\nCopied /om:view output to clipboard.` or `\n\nWarning: failed to copy …`; clipboard payload = CONTENT ONLY (no copy-status suffix).

### Decisive source
```ts
const notifyWithCopy = async (output: string) => {
	const copied = await copyToClipboard(output).catch(() => false);
	ctx.ui.notify(copied ? `${output}\n\nCopied …` : `${output}\n\nWarning: failed to copy …`, "info");
};
// clipboard.ts — ordered fallback ladder, first success wins:
case "darwin":  return [{ command: "pbcopy", args: [] }];
case "win32":   return [{ command: "clip", args: [] }];
default:        return [ wl-copy, xclip -selection clipboard, xsel --clipboard --input, termux-clipboard-set ];
// runClipboardCommand: spawn stdin-piped, stdio ignore, 2s timeout ⇒ kill ⇒ false;
// 'error'/'close(code!==0)' ⇒ false; child.stdin.on("error") swallowed
```

**Flow:** `firstArg` accepts array / raw string / `{mode}` object forms → default renders `visibleProjection`, `"full"` renders `fullProjection` (dropped observations excluded via tombstone fold), anything else prints usage WITHOUT copying → always attempt exactly one clipboard write for valid modes even on empty memory.
**Invariant:** The clipboard receives clean memory content while only the NOTIFY channel carries the success/failure suffix — so pasted output never contains UI noise. Copy failure must never suppress the rendering (view still shown with a warning). Unknown args copy nothing (side-effect-free usage error). The runner ladder tolerates missing binaries (spawn error → try next) and hangs (2s timeout).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "registerStatusCommand registerViewCommand diffProjection copyTextToClipboard getClipboardCommands", limit: 10 });
```
(Direct tests: `tests/status-command.test.ts:78` drift suffixes `+1 -1` over a mixed ledger incl. ignored V2 entries, :106 dual pool accounting `~19/20 target` vs `~5/40 visible`, :134 raw-source progress ignoring provider context, :197+ ratio-mode threshold fallbacks; `tests/view-command.test.ts:78` default=latest visible snapshot only, :100 full-view excludes dropped, :144 render survives copy failure, :160 unknown arg copies nothing; `tests/clipboard.test.ts:23` first-success-wins, :35 all-fail ⇒ false.)

## Verdict
Adopt the trust triad: count-based status with drift suffixes, separate progress clocks per automation stage, and content-only clipboard payloads with status confined to the notify channel. Adapt command names/platform ladders. Omit pi-tui render objects (host-specific); keep the copy-failure-degrades-gracefully contract.
