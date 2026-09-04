<!-- capsule-v2 -->
# task-spec-frontmatter-grammar — how does a Markdown-frontmatter spec parser validate user-authored files without ever throwing?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How should a strict-vocabulary Markdown intent grammar reject bad user content while still yielding a stable content hash so drift detection keeps working?

## Strict closed vocabularies; failures are data, and every failure carries a hash
**Path/Symbol:** `sdk/packages/core/src/tasks/specs/task-spec-parser.ts` (`parseAgendaTaskSpec` :235-431; `RESERVED_FIELDS` :22-37 = 14 keys; `ALLOWED_FIELDS` :39-56 = 16 keys; `hashContent` :144-150; `invalid` :221-232).
**Signature:** `parseAgendaTaskSpec(input: {specPath, raw, scope, workspaceRoot?}): AgendaTaskSpecParseResult` — discriminated union `{ok:true, specPath, contentHash, spec}` | `{ok:false, specPath, contentHash, error}`.
**Data Shape:** Frontmatter YAML mapping over a CLOSED vocabulary: 14 manager-owned RESERVED fields (status, instructions, revision, approvedRevision, createdBy, updatedBy, currentRunId, lastRunId, lastSessionId, error, createdAt, updatedAt, completedAt, archivedAt) are forbidden in user files; anything outside the 16 ALLOWED fields is unknown. Defaults live in the parser: `priority ?? 3`, `automationEligible: data.automationEligible !== false`.

### Decisive source
```ts
// Veto order matters: reserved (manager-owned) is checked BEFORE unknown,
// so a spoofed `status:` reports the security-meaningful error.
const reserved = Object.keys(data).filter((key) => RESERVED_FIELDS.has(key));
if (reserved.length > 0) {
	return invalid(input, contentHash,
		`operational field(s) cannot be set in a task spec: ${reserved.join(", ")}`);
}
const unknown = Object.keys(data).filter((key) => !ALLOWED_FIELDS.has(key));
if (unknown.length > 0) {
	return invalid(input, contentHash, `unknown task spec field(s): ${unknown.join(", ")}`);
}
// hashContent = sha256(JSON.stringify(frontmatter)) + "\n" + body.trim()
// — insertion-order JSON, whitespace-churn immune; BEFORE YAML parses it
// hashes {} + body so even unparseable files yield a stable non-canonical
// hash that can never match a DB projection.
```

**Flow:** splitFrontmatter (CRLF-normalized; missing frontmatter ⇒ invalid with `{}` hash) → YAML.parse inside try/catch (non-mapping or throw ⇒ invalid with `{}` hash) → hash over parsed data+body → reserved veto → unknown veto → workspace scope requires workspaceRoot → `type` ∈ 6-value enum → title required → trimmed body instructions required → priority integer 0..5 (default 3) → expiresAt ISO-8601 → availableAt strictly before expiresAt → resourcePaths string list → location normalization (THROWING helper caught here and folded into `invalid`) → modelSelection closed `{providerId, modelId?}` → maxIterations/timeoutSeconds positive ints → mode ∈ act|plan|yolo → automationEligible boolean.
**Invariant:** The parser never throws for invalid user content; every failure result carries a contentHash computed from what could be read, so the reconciler persists `ok:false` rows instead of crashing mid-walk and drift detection still sees a stable identity.
**Probe:** `grep -cF 'operational field(s) cannot be set in a task spec' sdk/packages/core/src/tasks/specs/task-spec-parser.ts` → 1 (:274); test pins (`task-spec-parser.test.ts`): "rejects manager-owned fields and invalid priorities", "rejects an availability window that ends before it begins" — both present.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.specs.task-spec-parser.parseAgendaTaskSpec" });
// observed: Function lines 235-431 verbatim, byte-equal to the checkout read
```

## Verdict
Adopt fail-as-data parsing with reserved-before-unknown veto order, hash-carrying failure results, and parser-local defaults. Adapt the field vocabularies and enum values to host domain types. Omit Cline's specific agenda semantics. Coverage: no_recorded_issue for both paths @ gen 2026-08-24T16:12:41Z; suite read whole (8 cases); runner-BLOCKED honestly (no node_modules).
