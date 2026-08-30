<!-- capsule-v2 -->
# Field-by-field config coercion + read-merge-write persistence — how do you keep a JSON settings file honest against hostile input?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you load user-editable JSON config so any garbage yields valid defaults, and write it back without destroying keys you don't own?

## coerceStatusConfig + loadStatusConfig/writeStatusConfig
**Path/Symbol:** `status.ts:42-90` (`coerceMode` :42-44, `coerceStatusConfig` :47-90), `index.ts:429-461` (`CONFIG_PATH` :429, `loadStatusConfig` :433-440, `writeStatusConfig` :443-461; import-time reload :463), command surface `index.ts:838-920` (`handleStatusCommand`), interactive `:923-1010` (`configureStatusInteractive`).
**Signature:** `coerceStatusConfig(raw: unknown): StatusConfig`; `writeStatusConfig(): void`.
**Data Shape:** `StatusConfig = { session: "widget"|"statusbar"|"off"; account: same; hideOnOtherProvider: boolean; lowBalanceHc: number|null }`.

### Decisive source
```ts
lowBalanceHc:
	typeof r.lowBalanceHc === "number" && Number.isFinite(r.lowBalanceHc) && r.lowBalanceHc > 0
		? r.lowBalanceHc
		: r.lowBalanceHc === null || r.lowBalanceHc === false
			? null          // explicit off, two spellings
			: d.lowBalanceHc,
```
And the non-destructive write:
```ts
let raw: Record<string, unknown> = {};
try {
	const existing = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
	if (existing && typeof existing === "object" && !Array.isArray(existing)) raw = existing;
} catch { /* No existing file — start fresh */ }
raw.session = statusConfig.session;
... // overwrite ONLY owned keys
fs.mkdirSync(path.dirname(CONFIG_PATH), { recursive: true });
```

**Flow:** module-load reads file → coerce (never throws; every field independently validated) → `/hypercharm-status` subcommands or interactive loop mutate in-memory → each mutation persists via read-existing→merge-owned-keys→write.
**Invariant:** coercion NEVER rejects a whole file — one bad field falls back to its default while good fields survive (smoke `:139-141` proves `{session:"bogus", lowBalanceHc:-3}` yields full defaults per-field). `null` AND `false` both mean "disable warning"; negative/non-finite numbers fall back to default rather than disabling. Writes preserve FOREIGN keys in the same file (read-modify-write of the raw object) and are best-effort: a failed write leaves the in-memory config still applied (`index.ts:459-460`). The command parser lowercases keys/values and validates BEFORE mutating (`handleStatusCommand` ladder).
**Probe:** `tests/status.smoke.ts:138-160` pins coercion incl. undefined/null/array inputs and both off-spellings. GREEN on Node 26.7.0 at HEAD 4520704. Persistence path untested upstream — caveat recorded.
**Coverage caveat:** status.ts fully covered by direct test; index.ts config IO untested.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "coerceStatusConfig", limit: 5 });
// → pi-hypercharm-provider.status.coerceStatusConfig status.ts 47-62
```

## Verdict
Adopt field-wise coercion + foreign-key-preserving writes for any extension config file. Adapt key names/modes. Omit the hypercharm-specific command UX.
