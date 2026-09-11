<!-- capsule-v2 -->
# CLI doctor JSON — how should a boot-free credential CLI emit versioned, secret-free JSON with meaningful exit codes?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** what is the contract between a script-consuming `--json` mode and human mode so the same diagnostics are safe to print and safe to exit on? (Diagnosis itself is `doctor-diagnostics.md`; this capsule owns the presentation plane.)

## Versioned secret-free JSON projection
**Path/Symbol:** `src/bin.ts:22 JSON_SCHEMA_VERSION = 1`, `src/bin.ts:115-121 doctorExitCode`, `src/bin.ts:124-140 doctorJson`, `src/bin.ts:142-144 printJson`, `src/bin.ts:47-52 safeMessage`, flag matrix in `run` (`src/bin.ts:152-170`).
**Signature:** `doctorJson(report: DiagnosticReport): Record<string, unknown>`; `doctorExitCode(report): number`; `safeMessage(error: unknown): string`; `printJson(value): void`.
**Data Shape:** doctor JSON `{ schemaVersion: 1, package, version, node, credentialFile: { state, mode? }, capabilities, providerConflict, hints, compatibility? }` — note `credentialFile.path` is structurally absent; status JSON `{ schemaVersion: 1, package: 'dsh-codex', status: 'signed-in'|'signed-out' }`; trusted-origins JSON `{ schemaVersion: 1, origins }`.

### Decisive source
```ts
function doctorExitCode(report: DiagnosticReport): number {
  const credentialFailure = report.credentialFile.state === 'permissions-too-broad'
    || report.credentialFile.state === 'not-a-regular-file'
    || report.credentialFile.state === 'unreadable-metadata'
  const compatibilityFailure = report.compatibility !== undefined && report.compatibility.status !== 'compatible'
  return credentialFailure || compatibilityFailure ? 1 : 0
}

/** Project the diagnostic report without its absolute credential pathname. */
function doctorJson(report: DiagnosticReport): Record<string, unknown> {
  const result: Record<string, unknown> = {
    schemaVersion: JSON_SCHEMA_VERSION,
    package: report.package,
    version: report.version,
    node: report.node,
    credentialFile: {
      state: report.credentialFile.state,
      ...report.credentialFile.mode === undefined ? {} : { mode: report.credentialFile.mode },
    },
    capabilities: report.capabilities,
    providerConflict: report.providerConflict,
    hints: report.hints,
  }
  if (report.compatibility !== undefined) result.compatibility = report.compatibility
  return result
}
// safeMessage strips JWT-like eyJ… tokens to '[redacted token]' and (code|token|
// refresh_token|access_token)=… query values to '$1[redacted]' before stderr.
```

**Flow:** argv → action whitelist + strict flag matrix (`--device-code` only with `login`; `--json` only with `doctor/status/trusted-origins`, never with login/logout/device-code; trust/untrust require exactly one bare origin argument) → action executes boot-free (no host startup) → `--json` prints exactly one line via `JSON.stringify` + newline; errors go to stderr prefixed `dsh-openai-codex:` and passed through `safeMessage`.
**Invariant:** exit code semantics are part of the contract — fatal credential-file states (`permissions-too-broad`, `not-a-regular-file`, `unreadable-metadata`) or any non-`compatible` dependency status exit 1 while merely-missing/expired-but-refreshable credentials do not; signed-out status exits 1; no JSON document may contain the absolute credential pathname, expiry timestamps, account ids, or token-shaped values even inside hints; unknown flags never execute an action.
**Probe:** `tests/bin.spec.ts` (12 tests: trust-origin roundtrip under a stubbed `DSH_HOME` incl. exact `{ schemaVersion: 1, origins: [] }`; help text; consistent error prefix; doctor --json matched object plus explicit `not.toHaveProperty('credentialFile.path')` and a six-item secret sweep incl. fixture tokens/account id/expiry; incompatible report → exit 1 with compatibility.status in JSON and no home path leaked; signed-in/out status JSON dropping all credential properties; five unsupported-flag combinations rejected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.bin\\.(doctorJson|doctorExitCode|safeMessage|printJson)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 4, has_more false; `get_code_snippet(doctorJson)` served lines 124-140 matching the pinned checkout.

## Verdict
Adopt the versioned single-line JSON documents, structural omission of sensitive fields (never post-hoc string filtering), exit codes that encode actionable failure only, strict flag matrices that reject before executing, and regex redaction as the last-resort stderr filter. Adapt document fields, prefix strings, and action vocabulary. Omit embedding diagnosis logic in the presentation layer or letting hints bypass the secret sweep. Coverage: `src/bin.ts` and `tests/bin.spec.ts` are `no_recorded_issue` + `metadata_match`; the full Vitest suite passed at this pin.
