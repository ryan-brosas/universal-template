<!-- capsule-v2 -->
# validateRequiredField + required-params split — which validation helper runs where and what counts as "present"?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** columnHelpers exports both validateParams (via import) and a local validateRequiredField — when is each used and what does each consider missing?

## validateRequiredField + required-params split
**Path/Symbol:** `packages/nocodb/src/helpers/columnHelpers.ts` — `validateRequiredField` (:588–596); contrast `validateParams` (imported :32, defined in `helpers/validateParams.ts`).
**Signature:** `validateRequiredField(payload: Record<string, any>, requiredProps: string[]) → boolean` — pure predicate, NO throw.
**Data Shape:** presence = `prop in payload && payload[prop] !== undefined && payload[prop] !== null`.

### Decisive source
```ts
// :588–596 verbatim:
export const validateRequiredField = (
  payload: Record<string, any>,
  requiredProps: string[],
) => {
  return requiredProps.every(
    (prop) =>
      prop in payload && payload[prop] !== undefined && payload[prop] !== null,
  );
};
```

**Flow:** callers use the boolean form when absence is a VALID state needing custom branching (e.g. conditional flows), vs `validateParams` which throws NcError for missing params in request handlers.
**Invariant:** Empty-string and `false` PASS the presence test (only undefined/null fail); `in` check means explicit-null keys are caught by the second clause while absent keys by the first — the two clauses are not redundant for prototype-chain reasons.
**Probe:** `grep -c "payload[prop] !== undefined" packages/nocodb/src/helpers/columnHelpers.ts` → `1`.
**Coverage caveat:** grep-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "validateRequiredField validateParams", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-clause presence definition; keep the throw-vs-boolean division of labor between the two validators intact in any port.
