<!-- capsule-v2 -->
# Event-log-metadata family layout — why does one jar carry ELEVEN telemetry schemes instead of one?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How do you partition a telemetry catalog when different consumers (product analytics vs ML training vs tracing vs partner mapping) need different slices of the same event stream?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.pycharm.community.jar:event-log-metadata/` — 60 entries total (occurrence-exact): FUS ×20 (scheme+meta + 8 dictionaries×2 + dictionaries.json×2), and ten more families IJ_MAP, KOOG, LLMC, ML, MLSE, ML_FED, MP, MTHC, TBE, TRACE each exactly ×4 (`events-scheme.json` + `.meta` + `dictionaries/dictionaries.json` + its `.meta`).
**Signature:** family directory name = ALL-CAPS consumer code; every family ships the same `{events-scheme.json, events-scheme.json.meta}` pair; only FUS carries real dictionaries.
**Data Shape:** per-family group sets are DISJOINT personas of one platform: FUS v7613 = 716 groups (the product analytics corpus); ML v7591 = 8 groups (cloud.code.completion.relevance.model, findUsages.fileRanking, full.line…, full.method.generation, inline.completion.v2, ml.event.log, next.edit, pycharm.quickfix.imports); TRACE v7591 = 12 groups prefixed `trace.*` mirroring LLM/AI flows (trace.llm.chat.events, trace.next.edit, trace.terminal.ai, trace.ai.assistant.inline.prompt.llmc …); LLMC v7591 = 11 groups (llmc.inline.completion, llmc.recap, llmc.grouped.diff …); KOOG = 2 (koog.agent, koog.llm); MLSE=2, ML_FED=5 (federatedCompute.*), MP=2, MTHC=3 (matterhorn.*), TBE v5487=4, IJ_MAP v5547=0 (registry-only).
**`.meta` sidecar** = bare epoch-milliseconds string (FUS 1786456530000 → 2026-08-11T13:55:30Z; TRACE 2026-08-05) telling the server WHICH scheme generation produced an event — schemes regenerate on their own cadence, independent of build releases.

### Decisive source
```
unzip -l lib/intellij.pycharm.community.jar | grep 'event-log-metadata/'
→ 60 entries: 11× events-scheme.json, 11× .meta,
   18× FUS/dictionaries/* (9 files + metas), 20× remaining per-family dictionary.json pairs
```

**Flow:** one instrumentation call site can feed several pipelines because each family's scheme independently declares which groups it accepts; the shared group NAMING (e.g. `llm.chat.events` in LLMC vs `trace.llm.chat.events` in TRACE) shows families are derived views over one event vocabulary, not separate products.
**Invariant:** the FAMILY SET is cluster-stable — webstorm and rider ship the identical eleven family codes (verified via unzip -Z1 sweep) while group counts drift per product (rider FUS = 872 groups incl dotnet.*; pycharm = 716). A porter adding a new consumer adds a FAMILY DIRECTORY, not a field in an existing scheme.
**Probe:** from `<install>` root:
`unzip -l lib/intellij.pycharm.community.jar | grep -c 'event-log-metadata/[A-Z_]*/events-scheme.json$'` → `11`;
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json.meta` → `1786456530000`.
**Coverage caveat:** jar resource plane — not graph-indexed; unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no BM25 target for this plane (adjudicated wrong-plane). Deterministic retrieval:
`for p in ../webstorm ../rider ../pycharm; do unzip -Z1 $p/lib/*.jar 2>/dev/null | grep -c 'event-log-metadata/'; done` — non-zero rows identify the carrying jar(s) per product.

**Complements:** fus-events-scheme-grammar (file grammar), fus-telemetry-metadata-plane (pass 2; dictionary whitelists).

## Verdict
Adopt: multi-consumer telemetry as parallel versioned schemes with meta stamps, disjoint group personas, and per-family regeneration cadence. Adapt family taxonomy to your consumers. Omit the specific JetBrains consumer codes unless integrating with their backend.
