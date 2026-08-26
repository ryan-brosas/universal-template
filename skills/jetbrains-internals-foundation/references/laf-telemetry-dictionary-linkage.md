<!-- capsule-v2 -->
# LaF telemetry dictionary linkage — how do theme names become validated telemetry without shipping a theme registry?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** How can a UI setting as free-form as "which look and feel is active" produce clean analytics when themes are user-installable plugins with arbitrary names?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.pycharm.community.jar:event-log-metadata/FUS/dictionaries/look_and_feel.ndjson` (463 entries, 18,066 bytes) consumed via `{enum#look_and_feel}` field validators inside `event-log-metadata/FUS/events-scheme.json`.
**Signature:** ndjson = one whitelisted identifier per line, trailing space after each name (e.g. `"Acme "`) — the whitespace is part of the shipped format, not corruption.
**Data Shape:** names are telemetry-safe slugs of real theme ids: Acme, Apricode_Monokai, Arc_Dark, Arc_Dark_(Material), … plus platform entries (High contrast, IntelliJ Light, Dark). Sample fields validating against it: `theme_name:["{enum#look_and_feel}"]` (switch.ui and color.blindness event groups — exactly 3 `{enum#look_and_feel}` occurrences in FUS v7613).

### Decisive source
```
event-log-metadata/FUS/dictionaries/look_and_feel.ndjson (first lines):
Acme
Apricode_Monokai
Arc_Dark
Arc_Dark_(Material)
```
consumer side:
```json
"theme_name":["{enum#look_and_feel}"]
```

**Flow:** a custom theme plugin registers at runtime → its name either appears in the shipped dictionary (curated per release: 463 names cover the known ecosystem) or the event value falls outside every validator and drops — the vendor learns about POPULAR LISTED themes without ever receiving an unlisted plugin's arbitrary string.
**Invariant:** the dictionary IS the allowlist boundary for this dimension (extends fus-telemetry-metadata-plane's privacy invariant to UI settings); because it ships as data with its own `.meta` stamp (1785924049000-class stamps), the list refreshes on the scheme cadence, not the build cadence. A porter who ports the enum-ref grammar must also ship a refresh pipeline for referenced dictionaries or validation silently degrades to drop-everything.
**Probe:** from `<install>` root:
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/dictionaries/look_and_feel.ndjson | wc -l` → `462` (wc counts newline-terminated lines; 463th entry ends without newline);
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -o '{enum#look_and_feel}' | wc -l` → `3`;
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/dictionaries/python_packages.ndjson | wc -l` → `88888` (the largest sibling whitelist).
**Coverage caveat:** jar resource plane — not graph-indexed; unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no BM25 target (adjudicated wrong-plane). Deterministic retrieval:
`unzip -p <jar> event-log-metadata/FUS/dictionaries/look_and_feel.ndjson | head -5`.

**Complements:** fus-telemetry-metadata-plane (pass 2 — owns dictionaries.json registry + package whitelists; this capsule pins the CONSUMER-side enum# wiring and the LaF-specific curation).

## Verdict
Adopt: curated-name dictionaries as the privacy boundary for user-configurable identifiers; validate-by-enum-ref so the vocabulary evolves independently of code. Adapt slugification rules. Omit JetBrains' specific theme catalog unless you need their ecosystem census.
