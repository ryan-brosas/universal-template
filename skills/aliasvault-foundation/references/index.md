<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# AliasVault: E2E vault crypto & sync foundation

## Use this for
Use when building a zero-knowledge credential manager: SRP-based passwordless-feeling auth that never sends passwords to a server, offline-first encrypted vaults that sync by whole-blob revisions plus Last-Write-Wins merges, hybrid RSA+AES mail encryption, PIN/biometric unlock with burn-after-N attempts, or anti-phishing autofill matching. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./srp-wire-format-divergence.md` — which K/M1/M2 formulas keep Rust/.NET/JS SRP interopable despite the crate's different defaults.
- `./srp-ephemeral-validation.md` — rejecting B≡0/A≡0 (mod N) before session math, with Err-vs-None taxonomy.
- `./argon2-cross-client-params.md` — the {m:19456, t:2, p:1, len:32} Argon2id tuple every platform must replicate.
- `./srp-identity-vs-username.md` — verifier bound to an immutable random GUID so renames can't brick auth; legacy fallback ladder.
- `./server-fake-login-response.md` — cached fake verifiers + fresh ephemerals make unknown users indistinguishable at login-initiate.
- `./srp-session-cache-two-step.md` — identity-keyed 5-min ephemeral cache and the active-session vs wrong-password discriminator.
- `./refresh-token-reuse-window.md` — successor-linked rotation rows with a 30-second reuse window defeat concurrent-refresh races.
- `./device-scoped-revocation.md` — header-composed device identity driving three revocation scopes (logout / single-token / other-devices).
- `./password-change-rekey-flow.md` — old-password proof + new verifier + re-encrypted blob in one request, revoking other devices after commit.
- `./mobile-qr-login-handshake.md` — QR login lifecycle with RetrievedAt/FulfilledAt one-time latches and post-delivery key wiping.
- `./vault-revision-optimistic-concurrency.md` — append-only vault rows, revision-gated uploads returning 200-Outdated, KDF fields inherited verbatim.
- `./vault-retention-rules.md` — six grouped retention rules unioned into a keep-set over metadata-only projections.
- `./alias-claim-rate-limited-sync.md` — permanent email-claim reconciliation where limits silently skip instead of failing the sync.
- `./lww-merge-sql-generation.md` — the Rust core emits ordered SQL statements (strict-> LWW, local wins ties) without touching any DB.
- `./merge-composite-key-fieldvalues.md` — declarative per-table key config; FieldValues matches on (ItemId, FieldKey), not Id.
- `./prune-four-pass-trash-purge.md` — staged soft-delete → byte-reclaim trash purge whose timestamps propagate through sync.
- `./blob-presence-projection.md` — substr(Blob,1,1) projection keeps megabyte blobs out of JSON-over-FFI prune scans.
- `./client-merge-execution-plane.md` — TS wrapper sanitizing undefined↔null across serde-wasm-bindgen, executing statements, chunked export.
- `./email-hybrid-decryption.md` — per-email RSA-wrapped AES keys with a promise cache of non-extractable private keys keyed by public key.
- `./gzip-magic-fallback.md` — decrypt-then-sniff magic bytes lets one endpoint serve compressed and legacy payloads.
- `./pin-unlock-pepper-attempts.md` — device-bound pepper composited into the KDF salt; four attempts then delete everything.
- `./autolock-dual-timer.md` — setTimeout under 30s, persistent alarms over it, restart-stable re-arm, heartbeat honoring disabled=0.
- `./token-refresh-offline-taxonomy.md` — {success | auth-error⇒logout | transport-error⇒offline} triad with one retry budget.
- `./vault-unlock-method-ladder.md` — biometric→PIN→redirect fallback chain delegating verification to native code.
- `./sqlite-client-version-gate.md` — EF migrations history as version source; forward-compatible gate; transaction latch.
- `./clickjacking-click-validator.md` — fail-closed page-level opacity/filter scan gating autofill clicks.
- `./autofill-priority-ladder.md` — priority-ordered credential filter where URL-having credentials can never match by name.
- `./domain-extraction-boundaries.md` — URL acceptance ladder, suffix-anchored subdomain logic, two-level-TLD root extraction.
- `./unbiased-index-modulo-bias.md` — rejection-sampled uniform indexing plus opt-in deterministic seeding for generator UX.
- `./diceware-seeded-pipeline.md` — word→capitalize→join→salt pipeline with clamped settings and per-character coin flips.

## Capsule map
- **SRP crypto core** — `srp-wire-format-divergence`: crate-vs-wire divergence is three local functions (K=H(PAD(S)), RFC2945 M1, M2=H(A|M1|K)); swap any ⇒ interop breaks. `srp-ephemeral-validation`: reject peer ephemerals ≡0 mod N pre-session; Err = protocol violation, Ok(None) = bad proof. `argon2-cross-client-params`: Argon2id(19456KiB, 2it, 1lane, 32B) identical across clients; hash feeds SRP private key. `srp-identity-vs-username`: verifier binds to registration-time GUID identity, never the mutable username; both ends share the same fallback rule.
- **Server auth plane** — `server-fake-login-response`: per-request fresh ephemeral over a 4h-cached fake salt/verifier for unknown users. `srp-session-cache-two-step`: secret-b cached 5min keyed by srpIdentity; missing entry ≠ failed attempt. `refresh-token-reuse-window`: rotation rows linked by PreviousTokenValue; ≤30s replays return the SAME successor. `device-scoped-revocation`: device = client|UA|lang|appInstance; logout kills device, revoke-token kills one, password-change spares current. `password-change-rekey-flow`: initiate caches ephemeral, submit carries old-proof + new-verifier + new blob; ExecuteDeleteAsync others after commit. `mobile-qr-login-handshake`: DB-row challenge with FulfilledAt/RetrievedAt one-time latches, 10-min expiry checked at all three phases.
- **Vault sync & storage** — `vault-revision-optimistic-concurrency`: append-only blobs; stale clients get 200+Outdated; salt/verifier copied forward untouched. `vault-retention-rules`: Revision×3 ∪ Daily×2 ∪ Weekly×1 ∪ Monthly×1 ∪ DbVersion×2 ∪ LoginCredential×2, always keep newest, metadata-only projection. `alias-claim-rate-limited-sync`: claims never deleted, only disabled; limits silently skip with in-batch additive counting.
- **Merge & maintenance core (Rust)** — `lww-merge-sql-generation`: JSON in, ordered parameterized SQL out; strict > means ties go local; sorted columns = deterministic bytes. `merge-composite-key-fieldvalues`: static table registry declares composite keys (ItemId+FieldKey); dispatcher picks algorithm per table. `prune-four-pass-trash-purge`: flag items/children, orphan logos, then sweep historical blob bytes; every UPDATE stamps UpdatedAt so prunes sync. `blob-presence-projection`: 1-byte substr markers keep blob bytes out of FFI JSON while preserving emptiness semantics.
- **Client runtime planes** — `client-merge-execution-plane`: stringify-parse sanitization ×3, undefined→null params, VACUUM before 0x8000-chunked base64 export, skip-export short-circuit. `email-hybrid-decryption`: find key by public-key match → cached non-extractable CryptoKey → unwrap AES key → per-field GCM. `gzip-magic-fallback`: 0x1f8b sniff AFTER decryption; missing DecompressionStream throws explicitly. `pin-unlock-pepper-attempts`: SHA256(extensionId) appended to random salt, Argon2id 64MiB, attempt 4 deletes all five storage keys. `autolock-dual-timer`: <30s setTimeout vs ≥30s alarms; init must NOT reset existing alarms but may restore dead timeouts. `token-refresh-offline-taxonomy`: only 401/403 kill sessions; 5xx/network mean offline sentinel serverVersion '0.0.0'; 426 = upgrade-required everywhere. `vault-unlock-method-ladder`: biometric failure/cancel falls through to native PIN; redirect flag distinguishes self-heal from user action. `sqlite-client-version-gate`: __EFMigrationsHistory top row = version; incompatible throws typed error; repositories reset on blob reload; executeRaw filters control statements.
- **Autofill security** — `clickjacking-click-validator`: BODY/HTML opacity<0.9 or CSS filter ⇒ reject; exceptions count as detected (fail closed). `autofill-priority-ladder`: package→domain(sub-tiered)→root-word/title→text; best-tier-only output; credentials WITH URLs excluded from name matches. `domain-extraction-boundaries`: protocol legalizes dot-less hosts; suffix-anchored `.domain` subdomain test defeats example.com.evil.com; static two-level-TLD table for roots.
- **Generators** — `unbiased-index-modulo-bias`: accept-zone rejection sampling over u64; powers of two accept immediately; optional hex seed replays identical draws. `diceware-seeded-pipeline`: one index draw per word, per-char capitalization coins, len+1 sprinkle insertion, single alphanumeric salt char.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
AliasVault (AGPL-3.0 — patterns adopted, no code vendored), `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory project `ext-aliasvault` (ready FULL, 46,284 nodes / 99,722 edges, gen 2026-08-23T13:44Z, head==base==origin zero-drift; parse_partial ×22 = HTML fixtures/nginx/shell scripts, none cited). Monorepo: Rust core shared as WASM (browsers) + uniffi (iOS/Android), .NET 9 API/server, WXT browser extension, React Native mobile app.

## Full view (memory graph)
Revalidate `ext-aliasvault` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Graph note: BM25 search_graph resolves Function-class symbols (`srp_derive_session`, `merge_vaults`, `filter_credentials` verified line-exact); doc-shaped sections may need name_pattern queries. Coverage stdin-JSON sweep over 19 cited paths returned no_recorded_issue + generation_matches=true at pin. Upstream test suites exist in-file (`#[cfg(test)]`) and upstream (NUnit/jest) but cargo/dotnet/jest runners were unavailable in this clone — deterministic probe batteries substituted (84/84 GREEN).

## Boundaries
Adopt pure contracts: SRP wire math and validation order, LWW statement emission, retention keep-set algebra, priority-ladder filtering, attempt-ledger lockout, one-time challenge latches. Adapt host-specific integration: WebCrypto/native-crypto bindings, sql.js/SQLite drivers, IMemoryCache, EF Core, WXT storage, native bridge modules. Omit product-specific behavior: SpamOK email domains, AliasVault branding/i18n keys, docker/nginx deployment, importers, admin panel UI.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`alias-claim-rate-limited-sync.md`](./alias-claim-rate-limited-sync.md)
- [`argon2-cross-client-params.md`](./argon2-cross-client-params.md)
- [`autofill-priority-ladder.md`](./autofill-priority-ladder.md)
- [`autolock-dual-timer.md`](./autolock-dual-timer.md)
- [`blob-presence-projection.md`](./blob-presence-projection.md)
- [`clickjacking-click-validator.md`](./clickjacking-click-validator.md)
- [`client-merge-execution-plane.md`](./client-merge-execution-plane.md)
- [`device-scoped-revocation.md`](./device-scoped-revocation.md)
- [`diceware-seeded-pipeline.md`](./diceware-seeded-pipeline.md)
- [`domain-extraction-boundaries.md`](./domain-extraction-boundaries.md)
- [`email-hybrid-decryption.md`](./email-hybrid-decryption.md)
- [`gzip-magic-fallback.md`](./gzip-magic-fallback.md)
- [`lww-merge-sql-generation.md`](./lww-merge-sql-generation.md)
- [`merge-composite-key-fieldvalues.md`](./merge-composite-key-fieldvalues.md)
- [`mobile-qr-login-handshake.md`](./mobile-qr-login-handshake.md)
- [`password-change-rekey-flow.md`](./password-change-rekey-flow.md)
- [`pin-unlock-pepper-attempts.md`](./pin-unlock-pepper-attempts.md)
- [`prune-four-pass-trash-purge.md`](./prune-four-pass-trash-purge.md)
- [`refresh-token-reuse-window.md`](./refresh-token-reuse-window.md)
- [`server-fake-login-response.md`](./server-fake-login-response.md)
- [`sqlite-client-version-gate.md`](./sqlite-client-version-gate.md)
- [`srp-ephemeral-validation.md`](./srp-ephemeral-validation.md)
- [`srp-identity-vs-username.md`](./srp-identity-vs-username.md)
- [`srp-session-cache-two-step.md`](./srp-session-cache-two-step.md)
- [`srp-wire-format-divergence.md`](./srp-wire-format-divergence.md)
- [`token-refresh-offline-taxonomy.md`](./token-refresh-offline-taxonomy.md)
- [`unbiased-index-modulo-bias.md`](./unbiased-index-modulo-bias.md)
- [`vault-retention-rules.md`](./vault-retention-rules.md)
- [`vault-revision-optimistic-concurrency.md`](./vault-revision-optimistic-concurrency.md)
- [`vault-unlock-method-ladder.md`](./vault-unlock-method-ladder.md)
