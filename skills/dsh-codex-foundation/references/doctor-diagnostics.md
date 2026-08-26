<!-- capsule-v2 -->
# Secret-free doctor diagnostics — metadata-only credential states, conflict asserts, and non-mutating repair hints

**Source:** dsh-codex Apache-2.0 main@e3e54e206f7c829503c7e6eed378643ba0416792; Codebase Memory dsh-codex. **Question:** how can a diagnostic report pin credential-file state, provider conflicts, and dependency health while never opening secrets, starting OAuth, or mutating anything?

## diagnoseOpenAICodex / assertNoOpenAICodexProviderConflict / openAICodexConflictMessage
**Path/Symbol:** src/doctor.ts:63-116 (diagnose), 55-57 (assert), 49-52 (message); report shapes 14-46.
**Signature:** diagnoseOpenAICodex(options?: OpenAICodexDiagnosticOptions): Promise<OpenAICodexDiagnosticReport>; assertNoOpenAICodexProviderConflict(providerIds: readonly string[]): void; openAICodexConflictMessage(): string.
**Data Shape:** Report carries package/version/node, credentialFile {path, state: 'missing'|'owner-only'|'permissions-too-broad'|'not-a-regular-file'|'unreadable-metadata', mode?}, capabilities flags, providerConflict boolean, compatibility report, and hints[]. Options are all safe-to-obtain inputs: credentialPath override, registered provider ids, feature toggles, pure compatibility seam.

### Decisive source
~~~ts
try {
  const info = await lstat(path)
  if (!info.isFile()) {
    state = 'not-a-regular-file'
  } else if (process.platform === 'win32') {
    state = 'owner-only'
  } else {
    mode = (info.mode & 0o777).toString(8).padStart(3, '0')
    state = (info.mode & 0o077) === 0 ? 'owner-only' : 'permissions-too-broad'
  }
} catch (error: unknown) {
  state = (error as NodeJS.ErrnoException | null)?.code === 'ENOENT' ? 'missing' : 'unreadable-metadata'
}

export function assertNoOpenAICodexProviderConflict(providerIds: readonly string[]): void {
  if (providerIds.includes(OPENAI_CODEX_PROVIDER)) throw new Error(openAICodexConflictMessage())
}
~~~

**Flow:** lstat the credential path → classify into the five-state ladder (win32 collapses to owner-only) → check registered ids for the conflict flag → run detectCompatibility through the injectable seam → assemble ordered hints per finding (sign-in timing, mode restriction, file replacement, metadata unreadable, duplicate-bundle migration, compatibility repair) → return the report; separately, registration paths call the assert so a collision fails with the migration message before the generic registry error.
**Invariant:** metadata only — lstat never opens the OAuth document, refreshes a token, or starts authorization; the serialized report can never contain credential content (the test embeds a secret and asserts absence); hints advise but no files are changed automatically; the conflict assert fires before registry errors so users see an actionable migration hint; unknown compatibility is reported as unknown, never silently passed as compatible.
**Probe:** tests/doctor.spec.ts:18-71 — missing-file defaults, secret-absence with 0o644 file, conflict assert regex + providerConflict:true, incompatible pin hint /pin @earendil-works\/pi-ai to 0\.82\.1/, and unknown-compatibility honesty; executed via pnpm test -- tests/doctor.spec.ts.

## Get live surrounding code
**Retrieve:**
~~~ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.doctor\\.', limit: 10, fields: ['signature', 'name', 'file', 'lines'] });
~~~

## Verdict
Adopt the five-state metadata ladder, secret-free report discipline with an embedded-secret test, fail-before-generic-conflict assertion, and advisory-only hints for any plugin doctor command. Adapt state names, platform special cases, and hint text. Omit Codex version constants. Coverage no_recorded_issue + metadata_match for src/doctor.ts and tests/doctor.spec.ts; callers are src/bin.ts (run/doctorJson/doctorExitCode) and src/index.ts apply-time conflict assert.
