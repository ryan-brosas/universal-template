<!-- capsule-v2 -->
# Trusted-origin store — how do you persist an exact browser-origin allowlist owner-only so malformed or too-broad state fails closed and concurrent writers serialize?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should a remote-trust sidecar be normalized, validated, locked, and written so route-side trust checks can rely on it without ever echoing its contents?

## Exact-origin allowlist persistence
**Path/Symbol:** `src/trusted-origins.ts:96-121 normalizeTrustedOrigin`, `src/trusted-origins.ts:51-87 parseDocument`, `src/trusted-origins.ts:129-201 OpenAICodexTrustedOriginsStore` (readCurrent 137-149, list 152-154, has 157-160, trust 163-180, untrust 183-200).
**Signature:** `normalizeTrustedOrigin(rawOrigin: string): string`; `class OpenAICodexTrustedOriginsStore { has(origin: string): Promise<boolean>; list(): Promise<readonly string[]>; trust(origin: string): Promise<readonly string[]>; untrust(origin: string): Promise<readonly string[]> }`.
**Data Shape:** on-disk document `{ version: 1, mode: 'allowlist', origins: string[] }`, sorted and deduped; file `.openai-codex-trusted-origins.json` under the DSH home, written 0600 into a 0700 directory; ENOENT reads as an empty allowlist. This is the store half of the gate — the route-side decision ladder lives in `trusted-origin-gate.md`.

### Decisive source
```ts
async trust(origin: string): Promise<readonly string[]> {
  const normalized = normalizeTrustedOrigin(origin)
  await mkdir(dirname(this.filename), { recursive: true, mode: 0o700 })
  return withFileLock(this.filename, async () => {
    const current = await this.readCurrent()
    if (current.origins.includes(normalized)) return [...current.origins]
    const next: TrustedOriginsDocument = {
      version: TRUSTED_ORIGINS_FORMAT_VERSION,
      mode: TRUSTED_ORIGINS_MODE,
      origins: [...current.origins, normalized].sort(),
    }
    await writeFileAtomic(this.filename, `${JSON.stringify(next, null, 2)}\n`, {
      mode: 0o600,
      dirMode: 0o700,
    })
    return [...next.origins]
  })
}
// normalizeTrustedOrigin rejects: non-strings/empty/whitespace-padded input,
// non-http(s) protocols, embedded credentials, any path/query/fragment,
// wildcard hosts, CIDR-looking raw input, and 'null' origins.
```

**Flow:** normalize once up front → mkdir 0700 → acquire per-file lock → re-read current through the owner-only lstat gate (ENOENT → empty doc; otherwise strict parse rejecting unknown top-level fields, wrong `version`, wrong `mode`, non-string entries, invalid origins) → idempotent add/remove of the single normalized origin → atomic 0600 write of the sorted list → return a detached sorted copy.
**Invariant:** trust is exact-origin only — no wildcards, CIDR ranges, paths, credentials, or default-port aliases survive normalization (`HTTP://Example.test:80/` → `http://example.test`); a future `version`/`mode` is never silently accepted; a sidecar readable beyond its owner refuses with a `chmod 600` hint instead of being trusted; parse errors name only the filename, never document contents; every mutation re-reads under the lock so concurrent writers cannot lose entries.
**Probe:** `tests/trusted-origins.spec.ts` (13 cases: 3 normalization identities incl. IPv6 bracket form; 7 exact-origin rejections incl. `http://10.0.0.0/24`; persist+idempotent trust/untrust ending in the exact on-disk document at mode 0600; rejection of unknown field / `mode:'deny-all'` / 0644 broad mode; two concurrent `trust` calls both surviving).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.trusted-origins\\.(OpenAICodexTrustedOriginsStore|normalizeTrustedOrigin)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 2, has_more false; `get_code_snippet(normalizeTrustedOrigin)` served lines 96-121 matching the pinned checkout byte-for-byte.

## Verdict
Adopt the exact-origin grammar, the fail-closed document validation, owner-only mode gates on both read and write paths, and lock-serialized read-modify-write mutations returning detached sorted lists. Adapt the storage location, lock/write primitives, and CLI verbs around it; keep normalization as the single choke point every reader and writer passes through. Omit silently accepting future format versions/modes or trusting host-string prefixes. Coverage: `src/trusted-origins.ts` and `tests/trusted-origins.spec.ts` are `no_recorded_issue` + `metadata_match`; the full Vitest suite passed at this pin.
