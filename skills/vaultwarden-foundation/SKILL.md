---
name: vaultwarden-foundation
description: "Use when porting E2E-encrypted vault server machinery — master-password verification kernels, issuer-partitioned JWT realms, refresh/stamp session invalidation, type-driven RBAC guards, trusted-proxy client IP, 2FA challenge protocols with anti-replay, Send one-time links, SSRF-guarded egress, layered config engines, and org key-escrow recovery."
---
# vaultwarden: self-hosted Bitwarden-compatible vault server

## Use this for
Use when porting E2E-encrypted vault server machinery: master-password verification kernels, issuer-partitioned JWT realms, refresh/stamp session invalidation, type-driven RBAC guards, trusted-proxy client IP, 2FA challenge protocols with anti-replay, Send one-time links, SSRF-guarded egress, layered config engines, and org key-escrow recovery. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/pbkdf2-verification-kernel.md` — how a server verifies a client-derived secret without ever seeing the password.
- `references/jwt-issuer-realms.md` — one RSA keypair serving ten non-interchangeable token lifetimes via issuer suffixes.
- `references/refresh-rotation-ladder.md` — JWT validity → DB device-token existence → auth-method/config gate, and what kills the chain.
- `references/stamp-exception-grace.md` — route-scoped 2-minute grace window that lets password changes not log out the actor.
- `references/guard-chain-rbac.md` — Rocket FromRequest ladder encoding member/admin/manager/owner in types.
- `references/trusted-proxy-client-ip.md` — peer-trust-gated header parsing with IPv4-mapped canonicalization.
- `references/ratelimit-three-lanes.md` — governor limiters for login/admin/unauthenticated with startup-fail config.
- `references/password-login-ladder.md` — exact gate order of /connect/token password grant incl. auth-request bypass.
- `references/twofactor-challenge-envelope.md` — TwoFactorProviders2 challenge JSON, provider usability gates, remember tokens.
- `references/totp-replay-ledger.md` — last-used time-step high-water mark making 30-second codes single-use.
- `references/register-invitation-ladder.md` — stub accounts, consume-on-read invitations, dual wire-shape compat fold.
- `references/lazy-kdf-upgrade.md` — verify-then-ratchet work-factor migration without an offline rehash job.
- `references/key-rotation-fanout.md` — validate-first re-encryption fan-out, notification suppression, honest non-atomicity.
- `references/org-recovery-reset.md` — public-key escrow enrollment → admin reset with pre-mutation notification gate.
- `references/send-access-ladder.md` — typed error taxonomy plus atomic conditional-UPDATE access counters.
- `references/egress-ssrf-guard.md` — blocking hooks at parse, every DNS answer, and every redirect hop.
- `references/error-taxonomy-macros.md` — one Error carrying user/log split, code, event, silence; client-shaped envelopes.
- `references/make-config-layered-engine.md` — declarative table generating env/file/panel merging with file-over-env precedence and privacy masking.
- `references/sso-reconciliation-ladder.md` — identifier-first OIDC matching with explicit refusal taxonomy and refresh-time revocation.
- `references/timing-sidechannel-posture.md` — which channels are closed, masked, or accepted, documented in-source.
- `references/security-header-fairing.md` — central response hook with per-route CSP/CORP/X-Frame exceptions.
- `references/mpolicy-merge.md` — commutative max/OR policy reduction plus the shared protected-action proof struct.
- `references/device-handshake-authrequest.md` — approve-then-redeem passwordless login pinned to request IP + 5-minute TTL.
- `references/emergency-recovery-codes.md` — burn-on-use recovery codes and time-delayed escrow handover.
- `references/admin-session-gate.md` — purpose-isolated admin realm, fixed short TTL, own rate-limit lane.
- `references/retry-db-helpers.md` — two-cadence retry twins where zero means wait forever at boot.

## Capsule map
- **Crypto kernel** — `pbkdf2-verification-kernel`: PBKDF2-SHA256 over client hash, per-user salt+iterations column, ct_eq everywhere.
- **Token realms** — `jwt-issuer-realms`: `{origin}|{purpose}` issuers make token classes non-interchangeable under one keypair.
- **Sessions** — `refresh-rotation-ladder`: three-layer chain; `stamp-exception-grace`: route-scoped grace after stamp rotation kills all refresh tokens.
- **Authorization** — `guard-chain-rbac`: guard-type-as-RBAC; compiler forces checks by handler signature.
- **Network trust** — `trusted-proxy-client-ip`: header only from trusted CIDR peers, canonicalized; `ratelimit-three-lanes`: separate budgets per surface; `egress-ssrf-guard`: block at URL/resolve-answer/redirect-hop.
- **Login flows** — `password-login-ladder`: ordered gates incl. auth-request substitution; `sso-reconciliation-ladder`: four-way identity matching; `device-handshake-authrequest`: approve-then-redeem with IP pin.
- **Second factors** — `twofactor-challenge-envelope`: usability-filtered challenge map; `totp-replay-ledger`: monotone last-used step; `emergency-recovery-codes`: burn-on-use recovery + delayed escrow.
- **Account lifecycle** — `register-invitation-ladder`: stub completion + invitation take; `lazy-kdf-upgrade`: verify-then-ratchet; `key-rotation-fanout`: re-encrypt everything, suppress notifications, document non-atomicity; `org-recovery-reset`: escrowed admin reset gated by pre-notification.
- **Platform** — `error-taxonomy-macros`: policy-carrying Error + client envelopes; `make-config-layered-engine`: generated config layers with recorded overrides; `security-header-fairing`: route-aware headers; `mpolicy-merge`: commutative policy reduce; `admin-session-gate`: isolated short-TTL realm; `retry-db-helpers`: fixed-cadence retries.
- **Hardening** — `send-access-ladder`: metered-link admission via conditional UPDATE with typed OAuth-ish errors; `timing-sidechannel-posture`: closed/masked/accepted channel ledger incl. randomized register sleep.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf. Pass-1 thesis: the reusable core is not "a password manager" but the LAYERED TRUST LADDER — derive-then-verify crypto, purpose-partitioned tokens, type-driven guards, config-sensitive feature gates, and every destructive flow paired with a scoped escape hatch (stamp exception, remember token, escrow key).

## Provenance
vaultwarden (AGPL-3.0), `main@46d71107f5094460dd5ecbe1dbac6e6c71e5189a`; Codebase Memory project `ext-vaultwarden` (ready FULL 4,969n/23,031e gen 2026-08-23T12:03Z generation_matches=true; head==base==pin, zero drift vs origin/main at pass 1; parse_partial ×9 = Dockerfile.j2/migration SQL/playwright env only, none cited).

## Full view (memory graph)
Revalidate `ext-vaultwarden` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Coverage stdin-JSON on all 18 cited paths returned no_recorded_issue + metadata_match; BM25 resolves seam symbols line-exact but macro-generated config accessors need direct file cites (`src/config.rs:58`). Upstream ships only 3 unit-test functions (web_vault_compare, obscure_email ×2) + unstable-gated is_global fuzz tests — no runner exists for mined seams; all Probes are deterministic source pins per protocol.

## Boundaries
Adopt the pure contracts: derivation layering, issuer partitioning, guard composition, conditional-update counters, merge precedence, refusal taxonomies. Adapt: Rocket fairings/guards to your framework, diesel conditional updates to your ORM, governor to your limiter, config DSL to your runtime. Omit: Bitwarden client wire-compat envelopes unless targeting Bitwarden clients, legacy U2F/Duo-iframe paths, the web-vault static SPA itself, sso.rs/sso_client.rs OIDC transport internals (pass-2 target), mail templating bodies, notifications/push relay plumbing, icons service internals.
