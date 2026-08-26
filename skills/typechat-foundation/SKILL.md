---
name: typechat-foundation
description: "Canonical foundation leaf template. Copy manually; this library asset is not rendered by a slash command."
---
# TypeChat: structured-LLM-output foundation

## Use this for
Use when porting natural-language→structured-JSON pipelines: schema-driven prompting, LLM-output validation with one-shot repair, safe JSON program interpretation, retry/timeout/DoS hardening for model endpoints, or Python↔TypeScript schema bridging. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/result-contract.md` — the two-case Result union both ports share; value-not-exception propagation with a single unwrap throw site.
- `references/translate-loop.md` — extract-slice-parse-validate ladder plus the exactly-once repair turn; TS/Py failure-class and empty-object edge differences.
- `references/strip-nulls.md` — collect-then-delete null stripping for models that invent null optionals (TS-only seam).
- `references/model-fetch-loop.md` — transient-status retry taxonomy, temperature:0, malformed-200-as-Failure, shared attempt budget.
- `references/dos-hardening.md` — AbortSignal timeout incl body reads + incrementally-capped response reads; size violations never retry.
- `references/retry-after-and-routing.md` — Retry-After clamping with negative-header fallback; env-var provider routing; /responses URL auto-detection.
- `references/proxy-undici.md` — lazy undici dispatcher for HTTP(S)_PROXY/ALL_PROXY/NO_PROXY with actionable missing-dependency error.
- `references/ts-validator.md` — in-memory TypeScript compiler validating JSON via write-one-virtual-file; error-2740 missing-properties expansion.
- `references/json-program.md` — @steps/@func/@ref program → TS module emission and guarded interpreter; identifier+prototype injection wall.
- `references/zod-validator-printer.md` — Zod v4 dual surface: safeParse validation and named-type TypeScript printing from ONE schema object.
- `references/pydantic-validator.md` — strict-mode validation forced through a JSON round-trip (dict≠dataclass in strict mode); repair-ready issue rendering.
- `references/py-to-ts-schema.md` — TypedDict/dataclass/TypeAlias graph → TS declarations; accumulate-errors discipline; per-container optionality defaults.
- `references/inheritance-flattening.md` — base filtering (`_KNOWN_SPECIAL_BASES`) and identical-hint suppression deciding extends-vs-redeclare.
- `references/prompts-and-interactive.md` — byte-exact request/repair templates (quote-fence asymmetry between ports) and file/REPL session loops.
- `references/snapshot-harness.md` — per-interpreter-version syrupy snapshots pinning generated schemas; how to adjudicate version-skew.
- `references/example-patterns.md` — preamble-as-history, validator-subclass program hosts, UnknownText escape-member idioms.
- `references/httpx-client-lifecycle.md` — eager AsyncClient + explicit-close ownership; `__del__` close silently no-ops once the loop is gone.
- `references/py-complete-wire-divergences.md` — Python complete() retries malformed-200 bodies via bare-cast + generic except; null content coerces to Success(""); Azure dual-auth + empty-org headers.
- `references/classification-router-seam.md` — classify-then-dispatch over a single-field translator; open class union in BOTH ports; callable→null prompt-table serialization.
- `references/public-surface-contract.md` — py 13-name `__all__` omits HttpxLanguageModel (private-path mock seam); ts root barrel is result/model/typechat only, validators behind subpaths.
- `references/upstream-ci-gates.md` — CI enforces pyright+pytest ×4 interpreters but ONLY builds TypeScript; TS suites are local-only evidence.
- `references/py-offline-model-fakes.md` — zero-network test contract: fake the model interface (`FixedModel` complete() override) for loop/prompt behavior, swap the private `_async_client` for MockTransport for wire behavior; whole-conversation amber snapshots.

## Capsule map
- **Result & loop** — `result-contract`, `translate-loop`, `strip-nulls`: Success/Failure values feed a single extraction→validation→one-repair pipeline.
- **Model transport** — `model-fetch-loop`, `dos-hardening`, `retry-after-and-routing`, `proxy-undici`: fetch/httpx client with transient-only retries, server-negotiated backoff, timeout+size caps, optional egress proxy.
- **Validators** — `ts-validator`, `zod-validator-printer`, `pydantic-validator`: three interchangeable schema engines behind one `validate(json) -> Result<T>` contract.
- **Program plane** — `json-program`: compile-to-typecheck + sandboxed interpreter for function-call programs over an API.
- **Schema compiler** — `py-to-ts-schema`, `inheritance-flattening`: Python typing graph → TypeScript prompt schema with accumulated errors.
- **Surfaces & evidence** — `prompts-and-interactive`, `snapshot-harness`, `example-patterns`, `py-offline-model-fakes`: exact prompt wording, versioned snapshot tests, sanctioned composition seams, and the two-injection-point offline test contract.
- **Lifecycle & parity** — `httpx-client-lifecycle`, `py-complete-wire-divergences`: client ownership/close ladder and the Python↔TS failure-contract divergences a cross-port host must reconcile.
- **Composition & packaging** — `classification-router-seam`, `public-surface-contract`, `upstream-ci-gates`: multi-agent routing over translators, per-port export discipline, and which suites upstream CI actually enforces.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
TypeChat by Microsoft (MIT), `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory project `typechat` (pass 2 FULL re-index under this name — prior project `ext-typechat` is DEAD and all capsule citations repaired to the live name; ready 1,686n/5,054e gen 2026-08-25T19:58:29Z, head==base==pin, zero drift vs pass-1 pin; parse_partial ×1 = python/pyrightconfig.json :15-16, uncited; not_indexed = .env.example/jpeg/.db by design). Pass 3 re-verified the same pin with zero drift and EXECUTED the repo-owned `pytest -vv` fleet live at Python 3.14.7: 22 passed, 17 snapshots passed — probe sections in five capsules upgraded to executed-run evidence; coverage caveat added: `__snapshots__/test_translator.ambr` is absent from the graph's python/tests File inventory (amber files not graph-visible) and is cited from direct read only.

## Full view (memory graph)
Revalidate `typechat` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the result-union contract, translate/repair ladder, retry/hardening taxonomy, and schema-compiler semantics as pure portable behavior. Adapt transport mechanics (fetch vs httpx), prompt fence characters, knob names/units, and printer output style to the host language. Omit product surfaces (site/, tools/scripts), example app scaffolding, and the deprecated coffeeshop module except as conversion-parity evidence.
