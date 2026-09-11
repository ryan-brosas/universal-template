<!-- capsule-v2 -->
# pg math function guards — which scalar functions need NaN-domain guards, and how do persisted legacy names reach them?

**Source:** NocoDB AGPL-3.0 `develop@640fe3b06fb2`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When a formula function maps to a plain SQL name via string alias, why can upgraded guards miss old columns, and which functions need IEEE guards vs none?

## Connected graph-selected seam
**Path/Symbol:** `packages/nocodb/src/db/functionMappings/pg.ts` (MAX/GREATEST :96–:119, POW/POWER :120–:128, LOG :130–:138, SQRT :139–:143, ROUND :169–:180, MOD :439–:441).
**Signature:** MapFnArgs handlers: `async ({ fn, knex, pt }: MapFnArgs) => ({ builder })`.
**Data Shape:** `pt.arguments[i].dataType` drives the all-numeric gate; builders emit `knex.raw` composed from rendered argument builders.

### Decisive source
```ts
// `greatest` is the same handler under the name older columns stored: when a
// mapping is a plain string alias, mapFunctionName rewrites pt.callee.name and
// that rewritten tree is persisted, so a MAX column created before this became
// a function still arrives as `greatest` and would otherwise skip the guard.
GREATEST: async (args: MapFnArgs) => pg.MAX(args),
MAX: async ({ fn, knex, pt }: MapFnArgs) => {
  ...
  const stripped = args.map((arg) => stripNaNSql(arg));
  return { builder: knex.raw(
    `COALESCE(greatest(${stripped.join(', ')}), greatest(${args.join(', ')}))`,
  )};
},
```

**Flow:** MAX: if not all args NUMERIC → plain `greatest(...)`; else strip NaN from every operand, take `greatest(stripped…)`, COALESCE against unstripped `greatest(raw…)` so an all-NaN list yields NaN instead of blanking. POWER/SQRT/LOG/MOD wrap their args in `ieeePowerSql/ieeeSqrtSql/ieeeLog(Base)Sql/ieeeModuloSql`. ROUND adds an isFinite CASE because ROUND casts to numeric, which raises on ±Infinity/NaN at pg<14 — rounding a non-finite value IS the value anyway.
**Invariant:** (1) Persisted-tree alias trap: `mapFunctionName` rewrites string-alias callees (`MAX`→`greatest`, `POWER`→`pow`) AND persists the rewritten tree — old columns arrive under the LOWERCASE name, so every guarded function needs its lowercase twin entry routing back to the same handler (GREATEST→pg.MAX, POW→pg.POWER). SQRT needs no twin: `'sqrt'` uppercases back to SQRT and hits its own key. (2) LEAST needs NO NaN guard — pg ranks NaN above every number so it can never win a minimum. (3) MAX's double-evaluation COALESCE preserves all-NaN→NaN semantics rather than blanking.
**Probe:** `grep -n "GREATEST:\|POW:" packages/nocodb/src/db/functionMappings/pg.ts` → :96/:124; `sed -n '96,99p'` twin comment verified. No upstream unit suite (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "functionMappings pg POWER MAX ROUND MOD", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the persisted-name twin-entry pattern for any guard added to a formerly-string-mapped function, the LEAST-needs-no-guard asymmetry, and the all-NaN fallback; adapt function vocabulary to host. Caveat: no direct upstream test.
