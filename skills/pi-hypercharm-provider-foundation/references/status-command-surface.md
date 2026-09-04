<!-- capsule-v2 -->
# /hypercharm-status command + interactive loop — how do you expose settings through both a slash grammar and a cycling TUI menu over ONE config object?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider` (node `pi-hypercharm-provider.handleStatusCommand`, `index.ts:838-920`). **Question:** What is the porting contract for the command surface — token grammar, validation, persistence ordering, and the headless fallback?

## One parser, one writer, notify-per-action
**Path/Symbol:** `handleStatusCommand` `index.ts:838-920`; usage string `STATUS_USAGE` :835-836; summary projector `statusSummary()` :830-833; interactive twin `configureStatusInteractive` :923-1010; persistence via `writeStatusConfig` :443-461 (capsuled separately).
**Signature:** `handleStatusCommand(args: string, ctx: ExtensionContext): Promise<void>`; `statusSummary(): string`; `configureStatusInteractive(ctx): Promise<void>`.
**Data Shape:** mutates module-singleton `statusConfig` in place then persists; `lowBalanceHc: number | null` where null means "off" — the SAME tri-state the coercion capsule covers on the read side.

### Decisive source
```ts
const tokens = args.trim().split(/\s+/).filter(Boolean);
if (tokens.length === 0) {
	if (!ctx.hasUI) { ctx.ui.notify(statusSummary(), "info"); return; }
	await configureStatusInteractive(ctx);   // UI present → menu, not help text
	return;
}
const [rawKey, rawValue] = tokens;
const key = rawKey.toLowerCase(); const value = rawValue?.toLowerCase();
```
```ts
// lowBalance leg: "off" is the ONLY way to reach null
if (key === "lowbalance" && tokens.length === 2) {
	if (value === "off") statusConfig.lowBalanceHc = null;
	else {
		const n = Number(value);
		if (!Number.isFinite(n) || n <= 0) { ctx.ui.notify(STATUS_USAGE, "error"); return; }
		statusConfig.lowBalanceHc = n;
	}
	writeStatusConfig(); updateStatus(ctx);
	ctx.ui.notify(`HyperCharm status. ${statusSummary()}`, "info");
	return;
}
```

**Flow:** empty args → headless prints `statusSummary()` ("session=…, account=…, hideOnOtherProvider=…, lowBalanceHc=off|<n>") and a UI host opens the interactive menu → `refresh`: sets `metaFetched = false`, awaits forced credits + meta fetches, notifies with balance → `reset`: replaces config with `{...DEFAULT_STATUS_CONFIG}` and persists → `session|account <widget|statusbar|off>` and `hide true|false` validate against closed value sets before any write.
**Invariant:** EVERY accepted mutation follows write→render→confirm (`writeStatusConfig()` then `updateStatus(ctx)` then a `notify` quoting `statusSummary()`), and every rejected input answers with the single `STATUS_USAGE` line — no silent accepts, no silent rejects. `tokens.length === 2` is enforced per-leg so trailing junk fails loudly. The interactive loop cycles modes with `(index+1) % modes.length` over `["widget","statusbar","off"]`, persists after every toggle, triggers a forced credits+meta refresh whenever account leaves "off", offers low-balance presets `["off","10","25","50","100","200","500"]` with the current value spliced-in-preserving-order when custom (`presets.includes(current) ? presets : [current, ...presets]`), treats select-cancel (`undefined`) as Done-with-final-render, and never exits itself — only the user closes it. Headless (`!ctx.hasUI`) NEVER opens menus: it prints the summary instead of USAGE because there is no input channel to correct.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-hypercharm-provider && grep -cF "Usage: /hypercharm-status" index.ts'` → 1; `grep -c "Number.isFinite(n) || n <= 0" index.ts` → 1; `grep -cF '"off", "10", "25", "50", "100", "200", "500"' index.ts` → 1; `grep -c "% modes.length" index.ts` → 1. Runtime path untested upstream — coverage caveat recorded.
**Coverage caveat:** command surface has no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "handleStatusCommand configureStatusInteractive", limit: 3 });
```

## Verdict
Adopt the token grammar shape, write-render-confirm ordering, closed-set validation with a single usage string, and the headless-summary fallback. Adapt command name, notify plumbing, and preset values to your host. Omit hyper.charm.land recharge URL copy.
