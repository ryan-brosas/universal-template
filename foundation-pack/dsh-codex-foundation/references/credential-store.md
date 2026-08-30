<!-- capsule-v2 -->
# Owner-only credential store — file-backed OAuth persistence with strict document validation

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how to persist a single OAuth credential to an owner-only file so that reads fail closed on malformed or over-broad documents, cross-instance writes serialize, and callers can never mutate the stored credential through the returned copy?

## OpenAICodexCredentialStore
**Path/Symbol:** `src/store.ts:OpenAICodexCredentialStore` (105-172), `src/store.ts:readCurrent` (117-127), `src/store.ts:modify` (142-164), `src/store.ts:delete` (167-171), `src/store.ts:parseDocument` (53-88), `src/store.ts:assertOwnerOnly` (32-50), `src/store.ts:openAICodexAuthPath` (100-102), `src/store.ts:isENOENT` (27-29), `src/store.ts:cloneCredential` (91-93).
**Signature:** `class OpenAICodexCredentialStore implements CredentialStore { constructor(filename = openAICodexAuthPath()); read(providerId): Promise<Credential|undefined>; list(): Promise<readonly CredentialInfo[]>; modify(providerId, fn): Promise<Credential|undefined>; delete(providerId): Promise<void> }`.
**Data Shape:** On-disk `AuthDocument` = `{ version: 1, credential: OAuthCredential }`. `OAuthCredential` = `{ type: 'oauth', access: string, refresh: string, expires: number, accountId: string }`. The store owns exactly one provider id `OPENAI_CODEX_PROVIDER = 'openai-codex'`; `read`/`list`/`delete` return empty/undefined for any other id, and `modify` throws for a foreign id. `modify` writes `mode 0o600` with `dirMode 0o700` and returns a `structuredClone` copy.

### Decisive source
```ts
// src/store.ts — strict document validation (no token-bearing input echoed)
function parseDocument(text: string, filename: string): AuthDocument {
  let value: unknown
  try { value = JSON.parse(text) }
  catch { throw new Error(`openai-codex: ${filename} is not valid JSON`) }
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`openai-codex: ${filename} must contain an object`)
  }
  const document = value as Record<string, unknown>
  if (document['version'] !== AUTH_FORMAT_VERSION) {
    throw new Error(`openai-codex: ${filename} has unsupported auth format version ${String(document['version'])}`)
  }
  if (Object.keys(document).some(key => key !== 'version' && key !== 'credential')) {
    throw new Error(`openai-codex: ${filename} contains an unknown top-level field`)
  }
  // ... credential must be object, keys ⊆ {type,access,refresh,expires,accountId},
  //     type === 'oauth', access/refresh/accountId non-empty strings,
  //     expires positive finite number
  return { version: AUTH_FORMAT_VERSION, credential: credential as unknown as OAuthCredential }
}

// Owner-only gate: reject a document readable beyond its owner (POSIX only)
async function assertOwnerOnly(filename: string): Promise<void> {
  let mode: number
  try { mode = (await stat(filename)).mode }
  catch (error) { if (isENOENT(error)) return; throw error }
  if (process.platform === 'win32') return
  if ((mode & 0o077) !== 0) {
    throw new Error(`openai-codex: ${filename} is readable beyond its owner (mode ${(mode & 0o777).toString(8)});`
      + ` run "chmod 600 ${filename}" before starting again`)
  }
}

// modify: serialize writers, validate candidate, atomic write, detach copy
async modify(providerId: string, fn) {
  if (providerId !== OPENAI_CODEX_PROVIDER) {
    throw new Error(`openai-codex: credential store does not own provider "${providerId}"`)
  }
  await mkdir(dirname(this.filename), { recursive: true, mode: 0o700 })
  return withFileLock(this.filename, async () => {
    const current = await this.readCurrent()
    const candidate = await fn(current)
    if (candidate === undefined) return current
    const document = parseDocument(JSON.stringify({ version: AUTH_FORMAT_VERSION, credential: candidate }), this.filename)
    await writeFileAtomic(this.filename, `${JSON.stringify(document, null, 2)}\n`, { mode: 0o600, dirMode: 0o700 })
    return cloneCredential(document.credential)
  })
}
```

**Flow:** `read`/`list` call `readCurrent` → `assertOwnerOnly` (absent path is fine, over-broad mode throws) → `readFile` (ENOENT → `undefined`) → `parseDocument` → return a `structuredClone` copy. `modify` checks provider ownership, `mkdir`s the parent `0o700`, then under `withFileLock` reads current, applies `fn`, re-validates the candidate via `parseDocument`, and `writeFileAtomic`s with `0o600`/`0o700`; `undefined` candidate leaves the file untouched and returns current. `delete` `rm`s under the same lock; a foreign id is a no-op.
**Invariant:** the stored credential is never mutated by a caller (every read returns a detached `structuredClone`); the document is validated fail-closed before every read and every write (unknown fields, wrong version, malformed credential, non-`oauth` type, empty/`expires<=0` all reject); a document readable beyond its owner is refused on POSIX; concurrent `modify` calls across instances serialize so each sees the prior committed value; errors never echo the token-bearing input.
**Probe:** `tests/store.spec.ts` — "persists, lists, detaches, and removes one OAuth credential owner-only", "serializes cross-instance refresh writes so each sees the prior value", "rejects malformed and over-broad documents without echoing their contents" (asserts `refresh` mentioned but `leaked-secret` absent), and "writes the versioned document and refuses provider ids it does not own".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", query: "OpenAICodexCredentialStore modify withFileLock writeFileAtomic owner-only", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the owner-only file-backed credential store: strict `parseDocument` validation (fail-closed on unknown fields/version/type/empty/expiry), `assertOwnerOnly` POSIX mode gate, `withFileLock`-serialized `modify` with atomic `0o600` writes, and `structuredClone` detachment so callers can never mutate persisted credentials. Adapt the document filename, the single owned provider id, and the `pi-ai` `CredentialStore` interface to the target provider. Omit the `OPENAI_CODEX_PROVIDER` route constant and the `@deepseek-ai/dsh-atomic-write`/`@deepseek-ai/dsh-home-paths` dependency specifics when porting (replace with any atomic-write + home-resolution primitive). Coverage: `src/store.ts` and `tests/store.spec.ts` both `no_recorded_issue` + `metadata_match`; the vitest runner is not installed in this read-only checkout, so deterministic probes were executed against the actual source (Node strip-types, external imports stubbed) and matched every test assertion (empty read, persist/list/read, detachment, `0o600` mode, delete, malformed-doc rejection without leaking the secret, over-broad-mode rejection, versioned doc, foreign-provider refusal, cross-instance serialization).
