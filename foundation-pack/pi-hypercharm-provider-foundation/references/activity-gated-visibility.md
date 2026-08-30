<!-- capsule-v2 -->
# Activity-gated status visibility + multi-slot UI reconciliation — when does a provider widget render, and how do you keep widget/statusbar slots consistent?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you show a footer line only when there is real activity (no half-empty glare on fresh or foreign-provider sessions), and reconcile two display surfaces without eating both footer slots?

## updateStatus visibility ladder
**Path/Symbol:** `index.ts:704-711` (`currentProviderId`), render core now `renderStatus` `index.ts:736-786` (entered via stale-guarded `updateStatus` :719-724, see stale-ctx-epoch-guard.md); gates `status.ts:146-156` (`buildSessionLine` undefined-on-empty :146-149, `accountHasData` :151-153), combined-status branch `index.ts:765-768`.
**Signature:** `updateStatus(ctx: ExtensionContext): void`; `currentProviderId(ctx): string | undefined`.
**Data Shape:** three UI slots — one below-editor widget (`WIDGET_KEY "hypercharm"`) + two status-bar keys (`hypercharm-session`, `hypercharm-account`); config `session`/`account` each independently `widget|statusbar|off`.

### Decisive source
```ts
function currentProviderId(ctx: ExtensionContext): string | undefined {
	// ctx.model is a getter that can throw on stale contexts
	try { return (ctx.model as any)?.provider; } catch { return undefined; }
}
...
const hasActivity = sessionStats.requests > 0 || sessionStats.spendHc > 0;
const sessionLine = statusConfig.session !== "off" ? buildSessionLine(sessionStats) : undefined;
// Show only after HyperCharm activity this session (like pi-neuralwatt):
// no empty-gap line on fresh sessions, no stale account glare on other providers' sessions.
const accountVisible = statusConfig.account !== "off" && accountHasData(account) && hasActivity;
...
if (sBar && aBar) {
	// Combined to avoid eating two footer slots
	ctx.ui.setStatus(STATUS_KEY_SESSION, ctx.ui.theme.fg(lowBalance ? "warning" : "dim", `${sBar} · ${aBar}`));
	ctx.ui.setStatus(STATUS_KEY_ACCOUNT, undefined);
}
```

**Flow:** read active provider defensively → `hideOnOtherProvider` ⇒ clear ALL three slots and return → compute per-zone lines under the activity gate → statusbar mode renders tier[0] only; widget mode renders full tier list → every path ends with all slots either set or explicitly `undefined`-cleared.
**Invariant:** NOTHING renders before this session's first provider turn completes (lifecycle comment `:41-46`) — fresh sessions and other providers' sessions see no half-empty line, and sessions without HyperCharm turns make zero status API calls. The stale-context getter throw is CAUGHT, not propagated. When both lines want statusbar placement they merge into ONE slot (footer slots are scarce). `clearAll()` explicitly unsets each key — never leaves stale strings from a previous state.
**Probe:** runtime rendering gated by pi events is untested upstream — deterministic probe: smoke pins the underlying pure gates (`buildSessionLine` returns undefined for zero stats at `tests/status.smoke.ts:42`, `accountHasData(acc({})) === false` / `acc({balance:0}) === true` distinguishing zero-balance from no-data at `:50-51`). Coverage caveat recorded.
**Coverage caveat:** event-driven paths untested upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "updateStatus", limit: 5 });
```

## Verdict
Adopt activity-gating, defensive model-getter access, explicit slot clearing, and single-slot merging. Adapt slot API to your host. Omit hypercharm config keys.
