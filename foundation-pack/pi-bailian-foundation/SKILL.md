---
name: pi-bailian-foundation
description: "Use when porting BYO-API-key subscription-provider machinery for coding-agent hosts — API-key-as-OAuth-credentials shim, prompt-only console login flow, prefix-laddered key validation, env-reference dual auth path, dual-region provider registration twins, zero-cost subscription model catalogs, and base-URL path-append delegation — capsule-v2 source maps with decisive excerpts and graph retrieval."
disable-model-invocation: true
---

# pi-bailian: Bailian Coding Plan provider-extension foundation

## Use this for
Use when adding a subscription/BYO-key service as a provider to a Pi-style coding-agent host: satisfying an OAuth-shaped credential interface without a token server, interactive key-entry login, per-region provider twins, or subscription model catalogs. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/apikey-as-oauth-credentials-shim.md` — how a static API key lives inside `OAuthCredentials` and survives the refresh contract.
- `references/env-reference-dual-auth-path.md` — `$VAR` apiKey reference + oauth handlers wired simultaneously so interactive login is optional UX, with three coequal credential-supply paths.
- `references/prompt-only-console-login-flow.md` — region-parameterized manual console login via `onPrompt`, fail-closed on invalid keys.
- `references/prefix-laddered-key-validator.md` — trim→empty→prefix→length ladder returning a result object, thrown only at the login boundary.
- `references/dual-region-provider-registration-twins.md` — two `registerProvider` calls sharing one env-var key reference and handler set.
- `references/zero-cost-subscription-model-catalog.md` — all-zero cost semantics and capability flags for subscription-metered plans.
- `references/base-url-path-append-delegation.md` — register the base path only; the host's `anthropic-messages` API appends `/v1/messages`.

## Capsule map
- **Credential shim** — `apikey-as-oauth-credentials-shim`: key duplicated into `refresh`+`access`, 1-year fake expiry; refresh re-extends expiry, never mutates key material.
- **Dual auth path** — `env-reference-dual-auth-path`: literal-`$` env reference + oauth handlers registered together; `/login`, env var, or hand-written auth.json are coequal supply paths — login is optional UX (resolution order is host-side).
- **Login flow** — `prompt-only-console-login-flow`: instructions through `callbacks.onPrompt` (no browser auto-open); invalid key throws before anything persists.
- **Validation** — `prefix-laddered-key-validator`: `{valid, error?}` result object at validator level; error text carries the console URL.
- **Registration** — `dual-region-provider-registration-twins`: one `$BAILIAN_CODING_PLAN_API_KEY` env reference shared by INTL/CN providers; CN delegates to shared login with `"cn"`.
- **Catalog** — `zero-cost-subscription-model-catalog`: 9-model rows, cost fields all 0 by design; ids identical across regions, names suffixed `(CN)`.
- **Transport** — `base-url-path-append-delegation`: `baseUrl` ends `/apps/anthropic`; appending `/v1/messages` yourself breaks the contract.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
pi-bailian (MIT), `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory project `pi-bailian` (FULL mode, generation 2026-08-25T20:09:00Z, 64 nodes / 77 edges, 0 skipped / 0 parse-partial; coverage checked `no_recorded_issue` on all cited paths incl. README.md and package.json at pass 2).

## Full view (memory graph)
Revalidate `pi-bailian` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Retrieval caveat observed at this pin: BM25 finds no Function node for the registration seam (it lives in the unnamed default export of `src/index.ts`) and zero hits for URL-constant vocabulary — retrieve those seams by module (`pi-bailian.src.models`) or read `src/index.ts` directly.

## Boundaries
Adopt the credential-shim shape, the fail-closed validation ladder, region-twin registration, zero-cost catalog semantics, and the base-URL append contract. Adapt provider ids, console URLs, model rows, and env-var names to your service. Omit Bailian-specific quota prose and usage-policy warnings; omit the test-local duplication of `validateApiKey` (export the real function instead when you port).
