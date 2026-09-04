<!-- capsule-v2 -->
# Dependency compatibility contract — exact-version evaluation, explicit unknown states, and a bounded manifest search

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how do you evaluate host/package compatibility honestly when versions may be missing, malformed, or undiscoverable?

## evaluateCompatibility / detectCompatibility (+ nodeStatus, packageEntry, aggregateStatus)
**Path/Symbol:** src/compatibility.ts:139-154 (evaluate), 186-196 (detect), 102-109 (nodeStatus), 111-122 (packageEntry), 132-136 (aggregate); contract constants 5-9 and COMPATIBILITY_CONTRACT 71-79; manifest search 159-183.
**Signature:** evaluateCompatibility(input?: CompatibilityEvaluationInput): CompatibilityReport; detectCompatibility(options?: CompatibilityDetectionOptions): Promise<CompatibilityReport>.
**Data Shape:** Report = {schemaVersion, status: 'compatible'|'incompatible'|'unknown', node: entry, packages: record of three entries}; each entry = {supported, installed|null, status}. Supported pins: node ^22.19.0 || >=24.0.0, DSH plugin API 0.1.0-rc.7 on two @deepseek-ai packages, pi-ai exactly 0.82.1.

### Decisive source
~~~ts
function compareVersion(left: string, right: string): CompatibilityStatus {
  return left === right ? 'compatible' : 'incompatible'
}

function nodeStatus(value: string | null | undefined): CompatibilityStatus {
  if (value === undefined || value === null || value.trim() === '') return 'unknown'
  const parsed = parseNodeVersion(value)   // strict vX.Y.Z regex, safe integers only
  if (parsed === undefined) return 'unknown'
  const [major, minor, patch] = parsed
  if (major === 22) return minor > 19 || (minor === 19 && patch >= 0) ? 'compatible' : 'incompatible'
  return major >= 24 ? 'compatible' : 'incompatible'
}

function aggregateStatus(entries) {
  if (entries.some(entry => entry.status === 'incompatible')) return 'incompatible'
  if (entries.some(entry => entry.status === 'unknown')) return 'unknown'
  return 'compatible'
}
~~~

**Flow:** collect installed values from caller input or process.version plus an injectable readPackageVersion seam → default seam resolves each package via import.meta.resolve and walks at most eight parent directories looking for a matching name+version package.json → classify each entry (missing/unparseable = unknown; exact string equality = compatible/incompatible; node uses its range rule) → aggregate with incompatible dominating unknown which dominates compatible.
**Invariant:** package compatibility is exact-version equality — no semver guessing that could mask breaking drift; anything unresolvable or malformed is unknown, never assumed compatible; the manifest search is depth-bounded and returns only versions/statuses (no filesystem detail escapes); the pure evaluateCompatibility accepts captured fixtures so diagnostics are testable without a real install; detection never writes files.
**Probe:** tests/doctor.spec.ts:50-71 drives the injected seam end to end ('incompatible' + repair hint for wrong pi-ai version; 'unknown' for garbage input); tests/compatibility.spec.ts covers the pure evaluator directly; executed via pnpm test -- tests/compatibility.spec.ts tests/doctor.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.compatibility\\.(evaluateCompatibility|detectCompatibility|aggregateStatus|nodeStatus)', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt exact-equality package checks, tri-state aggregation with unknown as first-class, strict node parsing, the injectable version-reader seam, and the depth-bounded manifest walk for any plugin compatibility checker. Adapt supported ranges/constants to the target ecosystem. Omit DSH-specific package lists. Coverage no_recorded_issue + metadata_match for src/compatibility.ts, tests/compatibility.spec.ts, src/doctor.ts.
