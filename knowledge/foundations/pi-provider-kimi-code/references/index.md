<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# pi-provider-kimi-code: request-construction foundation

## Use this for
Use when adapting a generic LLM-provider payload/stream pipeline to a constrained
vendor API: role/field normalization, cache-key injection, thinking-effort mapping,
file upload offloading, tool-schema size limits, and stream-event hygiene. Source
code and direct tests are ground truth; references carry decisive excerpts and graph
retrieval.

## Load the matching source dump
- `./payload-mutation-pipeline.md` — how do you apply every vendor-specific payload adaptation in one ordered, testable, in-place step list?
- `./file-upload-edge.md` — how do you recover a media upload from token rotation without failing the request?
- `./uploaded-file-cache.md` — how do you avoid re-uploading conversation images when payloads are rebuilt every turn?
- `./schema-type-backfill.md` — how do you make a strict server-side schema validator accept typeless JSON Schemas from arbitrary tools?
- `./tool-schema-dedup.md` — how do you fit large tool schemas under a per-tool byte limit without paying dedup cost every request?
- `./empty-response-filter.md` — how do you hide vendor-synthesized "(Empty response…)" text blocks without corrupting session content indices?
- `./stream-auth-retry.md` — how do you retry an auth-failed stream before any real event leaks into session history?
- `./layered-config-merge-ladder.md` — how do you layer defaults/home/project/env/runtime config without mutating shared defaults or persisting ad-hoc overrides?
- `./config-source-attribution.md` — how do you tell users which layer produced each effective config value?
- `./config-pointer-validation-projection.md` — how do you fail loudly on bad user config AND silently drop unknown keys in the same pass?
- `./env-patch-tolerance-asymmetry.md` — which environment-variable mistakes are fatal and which are silently ignored?
- `./quiet-vs-loud-config-reads.md` — should a malformed JSON config file crash the provider or degrade to defaults, and can both behaviors coexist legitimately?
- `./runtime-override-trio.md` — how do you give embedded hosts ephemeral config control without touching disk, and who actually uses it?
- `./resolved-store-overlay.md` — how does a stream function get resolved config it wasn't handed, without stale geometry?
- `./window-cap-tracking-sentinel.md` — how do you keep an unset maxTokens tracking contextWindow until the user sets it explicitly?

## Capsule map
- **Payload mutation pipeline** — `payload-mutation-pipeline`: one async in-place function, pure given its context; side effects enter via ctx.upload; ordering (extra_body → caps → thinking → tool_choice) is the contract.
- **File-upload IO edge** — `file-upload-edge`: images under threshold stay inline, videos always POST to /files, exactly one 401-drain-refresh-retry, null on failure keeps block inline.
- **Upload memo cache** — `uploaded-file-cache`: sha256(scope\0mime\0data) keys, 512-entry FIFO bound, scope-gated sharing, failures never cached.
- **Schema type back-fill** — `schema-type-backfill`: back-fill missing `type` from enum/const/structure keyword sets; skip combinator-keyed nodes; recurse properties/items/additionalProperties/anyOf-oneOf-allOf.
- **Tool schema dedup** — `tool-schema-dedup`: only >14 KB schemas; serialized-equality fragment collection; positive-savings $defs replacement; structural fingerprint cache with cycle/function/symbol/-0 handling.
- **Empty-response filter** — `empty-response-filter`: buffer while accumulated text is a prefix of the marker; suppress confirmed blocks; flush on divergence; clean content only at done; never splice mid-stream.
- **Stream auth retry** — `stream-auth-retry`: buffer synthetic start events until proof of life; one refresh+retry on first auth error (event or thrown); `$KIMI_API_KEY` passthrough expansion; null-preserving header merge.
- **Layered config merge ladder** — `layered-config-merge-ladder`: layer defaults/home/project/env/runtime config without mutating shared defaults or persisting ad-hoc overrides.
- **Config source attribution** — `config-source-attribution`: tell users which layer produced each effective config value.
- **Pointer validation projection** — `config-pointer-validation-projection`: fail loudly on bad user config AND silently drop unknown keys in the same pass.
- **Env patch tolerance asymmetry** — `env-patch-tolerance-asymmetry`: which environment-variable mistakes are fatal and which are silently ignored.
- **Quiet vs loud config reads** — `quiet-vs-loud-config-reads`: the request path dies on corrupt config; the settings UI falls back to defaults.
- **Runtime override trio** — `runtime-override-trio`: give embedded hosts ephemeral config control without touching disk, and who actually uses it.
- **Resolved-config store with live overlay** — `resolved-store-overlay`: a stream function gets config it wasn't handed, without stale geometry.
- **Window-cap tracking sentinel** — `window-cap-tracking-sentinel`: make maxTokens follow contextWindow until the user sets it explicitly.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed
porting question. Add one matching loader line and map entry; keep evidence in the
capsule, not this leaf. Next-pass seams live in the work record's NEXT-PASS TARGETS:
config plane, oauth/device plane, model discovery, kimi-native tools, usage accounting.

## Provenance
pi-provider-kimi-code (MIT), `main@794330400343d6f0cd0059635187b233c4d90273`;
Codebase Memory project `pi-provider-kimi-code` (mode full, generation
2026-08-25T20:08:56Z, 1408 nodes / 3802 edges, skipped=0, parse_partial=0;
coverage checked for every cited path).

## Full view (memory graph)
Revalidate `pi-provider-kimi-code` before porting: run `index_status`,
`check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`.
Record the graph root, branch, commit, mode, node/edge counts, freshness, and any
coverage caveats; source and direct tests decide shipped claims.

## Boundaries
Adopt the pure-context mutation pipeline, the hash-keyed bounded upload memo, the
savings-accounted dedup, and the buffered-filter/retry ladders as portable
contracts. Adapt protocol names (anthropic-messages / openai-completions), header
vocabularies, marker strings, byte thresholds, and env-var names to your host.
Omit Moonshot-specific wire facts (ms:// file URLs, prompt_cache_key semantics,
adaptive-thinking output_config shape) unless your target endpoint shares them,
and omit the pi-ai/pi-coding-agent host integration surface entirely.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`config-pointer-validation-projection.md`](./config-pointer-validation-projection.md)
- [`config-source-attribution.md`](./config-source-attribution.md)
- [`empty-response-filter.md`](./empty-response-filter.md)
- [`env-patch-tolerance-asymmetry.md`](./env-patch-tolerance-asymmetry.md)
- [`file-upload-edge.md`](./file-upload-edge.md)
- [`layered-config-merge-ladder.md`](./layered-config-merge-ladder.md)
- [`payload-mutation-pipeline.md`](./payload-mutation-pipeline.md)
- [`quiet-vs-loud-config-reads.md`](./quiet-vs-loud-config-reads.md)
- [`resolved-store-overlay.md`](./resolved-store-overlay.md)
- [`runtime-override-trio.md`](./runtime-override-trio.md)
- [`schema-type-backfill.md`](./schema-type-backfill.md)
- [`stream-auth-retry.md`](./stream-auth-retry.md)
- [`tool-schema-dedup.md`](./tool-schema-dedup.md)
- [`uploaded-file-cache.md`](./uploaded-file-cache.md)
- [`window-cap-tracking-sentinel.md`](./window-cap-tracking-sentinel.md)
