<!-- capsule-v2 -->
# Solid Show & Switch — how do control-flow components compile to memos with truthy-only equality and stale-read guards?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** How does non-keyed Show avoid re-rendering on same-truthiness changes, and how do callback children get narrowed values safely?

## flow.ts: Show condition chain + Switch priority ladder
**Path/Symbol:** `packages/solid/src/render/flow.ts:Show` (:101-149), `Switch` (:167-221), `narrowedError` (:16-19).
**Signature:** `Show(props: { when, keyed?, fallback?, children })`, `Switch(props: { fallback?, children: MatchElements })`.
**Data Shape:** `conditionValue = createMemo(() => props.when)`; for non-keyed a SECOND memo wraps it with `{ equals: (a, b) => !a === !b }`. Match children are raw props objects (`Match` returns `props as unknown as JSX.Element`) resolved via the `children()` helper.

### Decisive source
```ts
const condition = keyed
    ? conditionValue
    : createMemo(conditionValue, undefined,
        { equals: (a, b) => !a === !b });
return createMemo(() => {
      const c = condition();
      if (c) {
        const child = props.children;
        const fn = typeof child === "function" && child.length > 0;
        return fn
          ? untrack(() =>
              (child as any)(
                keyed ? (c as T) : () => {
                      if (!untrack(condition)) throw narrowedError("Show");
                      return conditionValue();
                    }
              )
            )
          : child;
      }
      return props.fallback;
});
```

**Flow:** truthiness-equality memo means 1 → 2 does NOT re-run children (same truthiness), only falsy↔truthy transitions do. Callback children (declared with a parameter, detected by `child.length > 0`) receive either the narrowed value (keyed) or a LAZY accessor that re-checks the condition on every read and THROWS the dev-narrowedError if read after the branch went false. Switch builds its ladder INSIDE one memo over `children()`: each Match contributes `prevFunc() ? undefined : mp.when` chained through closures so evaluation short-circuits at first truthy in declaration order.
**Invariant:** The accessor-guard pattern is the safety net for unmounting async callbacks: reading `item()` after the branch flipped throws instead of returning undefined. Match priority is array order of children, recomputed whenever the children EXPRESSION changes. `keyed` changes identity semantics: keyed=true re-renders when the value CHANGES (not just truthiness).
**Probe:** `grep -c 'equals: (a, b) => !a === !b' packages/solid/src/render/flow.ts` → `2` (Show + per-Match). Behavior pinned by test/rendering.spec.ts (:1-131).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "Show Switch Match condition keyed", limit: 10 });
```

## Verdict
Adopt truthiness-equality + lazy-narrowed-accessor contract for conditional rendering primitives. Adapt error message text freely. Omit keyed mode if your host only needs boolean conditions.
