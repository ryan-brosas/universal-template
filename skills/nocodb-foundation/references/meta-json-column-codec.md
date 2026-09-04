<!-- capsule-v2 -->
# Meta JSON column codec — how do object-valued columns survive the string-typed meta tables without corrupting reads?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** What is the one choke-point contract for storing JSON in a text column of the shared meta schema, and what happens on malformed data?

## parse/stringify with swallow-and-fallback, applied only to PRESENT props
**Path/Symbol:** `packages/nocodb/src/utils/modelUtils.ts` — parseMetaProp (:4–19), stringifyMetaProp (:21–36), prepareForDb (:38–52), prepareForResponse (:54–71).
**Signature:** `parseMetaProp(model, propName='meta', fallbackValue={})` · `stringifyMetaProp(model, propName='meta', fallbackValue='{}'): string|null` · `prepareForDb(model, props: string|string[]='meta')` · `prepareForResponse(model, props)`.
**Data Shape:** callers name the JSON-ish columns per model — Notification uses 'body' (models/Notification.ts), Audit uses 'details' (models/Audit.ts insert), most models use the default 'meta'.

### Decisive source
```ts
try {
  return typeof model[propName] === 'string' ? JSON.parse(model[propName]) : model[propName];
} catch { return fallbackValue; }              // parse: {} default, NEVER throws

return typeof model[propName] === 'string' || model[propName] === null
  ? model[propName]                             // idempotent: strings pass through untouched
  : JSON.stringify(model[propName]);            // null stays null (not "null")

props.forEach((prop) => {
  if (prop in model) {                          // presence gate: absent keys stay absent
    model[prop] = stringifyMetaProp(model, prop);
  }
});
```
(:12–18, :30–32, :45–49)

**Flow:** write path — service mutates plain objects → prepareForDb(model, '<col>') stringifies each named col IN PLACE → metaInsert2/metaUpdate persists text → read path — rows come back with string cols → prepareForResponse(row, '<col>') parses IN PLACE (Notification.list loops every row :90–93).
**Invariant:** both directions are IDEMPOTENT for already-(un)stringified values (string in → string out on write; object in → object out on read); malformed stored JSON degrades to the fallback ({}) instead of throwing — a poisoned row can never 500 a list endpoint; the `prop in model` gate means an absent key is never seeded with '{}' (absence survives round-trips); stringify maps null→null while parse's fallback only applies to THROWN parses. Fan-in is the portability evidence: parseMetaProp 48 call sites, prepareForDb 34, prepareForResponse 25, stringifyMetaProp 21 (search_graph counts @pin).
**Probe:** `grep -c "prop in model" packages/nocodb/src/utils/modelUtils.ts` (=2: db+response gates) · `grep -c "'{}'" packages/nocodb/src/utils/modelUtils.ts` (=1: stringify's fallbackValue default :24) · `grep -c "typeof model\\[propName\\] === 'string'" packages/nocodb/src/utils/modelUtils.ts` (=2: one per direction).
**Direct test:** none upstream for utils/modelUtils.ts — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", file_pattern: "*utils/modelUtils*", limit: 10 });
```

## Verdict
Adopt the two-function codec (idempotent, swallow-with-fallback, presence-gated application) for any text-column-JSON persistence; adapt fallback values and add telemetry on the swallowed-parse path if silent degradation is unacceptable in your host; omit the multi-prop array form if your models carry at most one JSON column. Coverage caveat: grep-pinned; behavior confirmed by direct read of all 126 lines.
