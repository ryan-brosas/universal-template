<!-- capsule-v2 -->
# stripNulls — how are model-invented null optional properties removed safely?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How do I strip null-valued properties (and nulls inside arrays) from parsed JSON without corrupting objects, and when is it needed?

## Recursive delete-after-collect
**Path/Symbol:** `typescript/src/typechat.ts:170-193` (`stripNulls`, module-private), toggled by `TypeChatJsonTranslator.stripNulls` (:27, default **false**) applied in `translate` :147-149.
**Signature:** `function stripNulls(obj: any): void` — mutates in place.
**Data Shape:** input is the freshly parsed JSON object; assumes no circular references (documented).

### Decisive source
```ts
if (value === null) {
    (keysToDelete ??= []).push(k);
}
else {
    if (Array.isArray(value)) {
        if (value.some(x => x === null)) {
            obj[k] = value.filter(x => x !== null);
        }
    }
    if (typeof value === "object") {
        stripNulls(value);
    }
}
if (keysToDelete) {
    for (const k of keysToDelete) {
        delete obj[k];
    }
}
```
**Flow:** single pass collects null-valued keys into a local list, filters nulls out of arrays immediately, recurses into plain objects, THEN deletes collected keys after iteration completes.
**Invariant:** deletion happens AFTER the for-in loop finishes — deleting during iteration would skip sibling keys. The docstring records WHY the flag exists: gpt-3.5-turbo-era models assign null to optional properties instead of omitting them, and schemas that don't permit null then fail validation. Default OFF means a porter who forgets to opt in gets the original strict behavior — the flag is per-application, not global.
**Probe:** `grep -c 'value.filter(x => x !== null)' typescript/src/typechat.ts` (=1); `grep -c 'attemptRepair:  true' typescript/src/typechat.ts` (=1 shows defaults live on the instance literal).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "typechat", query: "stripNulls null properties", limit: 3 });
// rank1 Function typescript/src/typechat.ts 170-193
```

## Verdict
Adopt the collect-then-delete pattern exactly (it is the safe for-in contract); adapt recursion depth guards only if host JSON may be cyclic; omit entirely for schemas that accept nulls — but keep it available because repair loops burn tokens re-asking for what a one-line strip fixes. Python port has NO equivalent — note this asymmetry in any cross-language host.
