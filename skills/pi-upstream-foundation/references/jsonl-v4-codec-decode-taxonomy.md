<!-- capsule-v2 -->
# JSONL v4 codec decode taxonomy — where is the syntax-vs-schema split made, and what else does the codec enforce before any line becomes state?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`. **Question:** A porter consumes the torn-tail rule ("truncate a syntactically broken final line, refuse semantic corruption") without knowing where the syntax/schema distinction is produced — what does the codec that creates it also enforce, and what happens to corrupt files at list time vs open time?

## Strict allow-list decode with a two-kind error taxonomy; listing tolerates, opening refuses
**Path/Symbol:** `packages/agent/src/harness/session/jsonl/codec.ts:decodeHeader` (:58-88), `parseMutation`/`decodeMutation` (:200-224), `encodeMutation` (:226-240); `packages/agent/src/harness/session/jsonl/errors.ts:JsonlDecodeError` (:4-12), `fileResult` (:14-24), `invalidFile` (:26-28).
**Signature:** `parseHeader(line): Result<JsonlV4Header, JsonlDecodeError>`; `parseMutation(line): Result<SessionMutation, JsonlDecodeError>`; `encodeMutation(mutation): string`; `class JsonlDecodeError extends Error { readonly kind: "syntax" | "schema" }`.
**Data Shape:** header = `{kind:"header", version:4, id, createdAt, cwd, parentSessionId?, legacyParentSessionPath?, metadata?}`. Mutations = four kinds (`entry`, `record`, `lane`, `fact`) with strict allow-lists: 7 entry types, 9 record types, 3 operation kinds (`run`, `compaction`, `navigation`). `JsonlDecodeError.kind` is the ONLY input the torn-tail repair consults.

### Decisive source
```ts
function parseObject(line: string): Record<string, unknown> {
	let value: unknown;
	try {
		value = JSON.parse(line);
	} catch (error) {
		throw new JsonlDecodeError("syntax", "is not valid JSON", error instanceof Error ? error : undefined);
	}
	if (!isObject(value)) throw new JsonlDecodeError("schema", "is not a JSON object");
	return value;
}
```
Header exclusivity rule (decodeHeader):
```ts
if (parentSessionId !== undefined && legacyParentSessionPath !== undefined) {
	throw new JsonlDecodeError("schema", "has both parentSessionId and legacyParentSessionPath");
}
```

**Flow:** every line goes through `parseObject` first (JSON.parse failure ⇒ `syntax`; non-object ⇒ `schema`) → header: version must be exactly 4 (there is NO v3 upgrade path in the codec — `legacyParentSessionPath` and `sourceFormat: 3|4` are metadata-compat riders for unresolved v3 parent paths, not a migration), parent fields are mutually exclusive, metadata must be an object → mutations: type/kind allow-lists, `custom` entries require `customType`, `operation_started` requires an object `intent` with a known kind, `operation_finished` requires `runId`, fact name/label may be `undefined` (a clear) but never a non-string → `encodeMutation` re-inserts `kind` and flattens the entry/record wrappers so the wire line is self-describing.
**Invariant:** the taxonomy is load-bearing OUTSIDE the codec: only `kind:"syntax"` on the final line is repairable (torn-tail capsule), everything else is corruption to surface. Tolerance is split by call site, not by the codec: list-time header parse failures are SKIPPED (`repo.ts:listJsonlSessionMetadata` — `if (!headerResult.ok) continue`, one corrupt file must not hide the other sessions), while open-time header failures throw `invalid_entry` (`storage.ts:76-77`) — a session you were asked to open must never silently degrade. `seq` must be a safe positive integer; timestamps a safe non-negative integer — both checked before any state application.
**Probe:** `packages/agent/test/harness/session/jsonl-codec.test.ts` (whole file, 182 lines): `"returns syntax and schema errors"` (:76-86 — `"{"` ⇒ syntax, `{kind:"unknown"}` ⇒ schema); header round-trips incl. the legacy-parent-path shape (:16-52); `it.each` rejects custom-without-customType, started-without-intent, finished-without-runId (:160-182). Cross-witness `packages/agent/test/harness/session/jsonl.test.ts:125-137` and :139-158: malformed header ⇒ `open` rejects `invalid_entry` while `list` returns only the valid sibling and the corrupt file stays byte-identical.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "JsonlDecodeError syntax schema parseMutation parseHeader codec", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the two-kind decode error taxonomy as the repair rule's input, strict type/kind allow-lists at decode (never trust the wire shape), list-skips/open-refuses tolerance split, and the parent-field exclusivity check. Adapt the error kinds to your serializer's vocabulary but keep syntax (unparseable) strictly weaker than schema (parseable, invalid). Omit the v3 rider fields unless you must read pre-v4 sessions — they are compatibility metadata, not a migration path. Coverage caveat: the codec has a dedicated test file at this pin; no test covers `encodeMutation` of a fact with a `null` (vs `undefined`) name — the type forbids it, decode rejects it, and the omission is intentional.
