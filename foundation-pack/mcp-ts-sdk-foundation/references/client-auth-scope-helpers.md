<!-- capsule-v2 -->
# OAuth scope-union helpers — how do you union and compare RFC 6749 scope strings without inventing semantics the spec does not have?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `typescript-sdk`. **Question:** What are the exact contracts of `computeScopeUnion` / `isStrictScopeSuperset`, including their deliberate non-normalizations?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/auth.ts`: `computeScopeUnion` (:602-611), `isStrictScopeSuperset` (:630-637); consumers: `streamableHttp._stepUpAuthorizeInner` (see step-up-scope-union.md for the transport ladder) + conformance test helper `withOAuthRetry.handle401`.
**Signature:** `computeScopeUnion(...scopes: ReadonlyArray<string | undefined>): string | undefined` · `isStrictScopeSuperset(union: string | undefined, current: string | undefined): boolean`
**Data Shape:** space-delimited scope strings per RFC 6749 §3.3; `undefined` means "absent".

### Decisive source
```ts
// :602-611 — first-seen-order Set dedup; all-empty ⇒ undefined
export function computeScopeUnion(...scopes: ReadonlyArray<string | undefined>): string | undefined {
    const seen = new Set<string>();
    for (const scope of scopes) {
        if (!scope) continue;
        for (const token of scope.split(/\s+/)) {
            if (token) seen.add(token);
        }
    }
    return seen.size > 0 ? [...seen].join(' ') : undefined;
}
// :630-637 — any union token outside current ⇒ true; absent current = EMPTY set
export function isStrictScopeSuperset(union: string | undefined, current: string | undefined): boolean {
    if (!union) return false;
    const currentSet = new Set((current ?? '').split(/\s+/).filter(Boolean));
    for (const token of union.split(/\s+/)) {
        if (token && !currentSet.has(token)) return true;
    }
    return false;
}
```

**Flow:** step-up feeds `(transport-tracked scope, token-granted scope, challenged scope)` into
`computeScopeUnion`, persists the union on the transport, then gates refresh-vs-fresh-auth on
`isStrictScopeSuperset(union, tokens?.scope)`.

**Invariant:** first-seen order preserved; whitespace runs (`/\s+/`) collapse; NO hierarchical
deduplication (`'admin'` + `'read'` stays `'admin read'` — the AS normalizes redundancy at
issuance, the spec's step-up flow does not require clients to). An absent token `scope` counts as
the EMPTY set, so a token that omits its scope field always reads "strictly exceeded" and forces a
fresh authorization rather than risking a refresh that silently drops widened scope (RFC 6749 §3.3
lets servers omit equal scope — this helper is deliberately conservative).

**Probe:** `packages/client/test/client/auth.test.ts` :196-216 (`computeScopeUnion` table:
`['read write','write admin'] → 'read write admin'`, `'  read   write  '` normalized,
hierarchical non-collapse) and :218-232 (`isStrictScopeSuperset` nine-row table incl.
`('read', 'read write') → false`, `('read', undefined) → true`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typescript-sdk", name_pattern: "^(computeScopeUnion|isStrictScopeSuperset)$", project_file: "auth.ts" });
// or: trace_path({ project: "typescript-sdk", function_name: "computeScopeUnion", direction: "both" })
```

## Verdict
Adopt both helpers verbatim as pure functions (no state, no I/O); adapt the empty-means-superset
conservatism only if your token store guarantees a materialized `scope`; omit hierarchical
deduplication everywhere — reimplementing it would break parity with the AS's own normalization.
Companion capsules: step-up-scope-union.md (transport ladder), auth.md (pass-1 flow overview).
