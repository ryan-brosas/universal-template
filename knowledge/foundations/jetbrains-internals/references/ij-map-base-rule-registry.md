<!-- capsule-v2 -->
# IJ_MAP base rule registry — why is the empty-groups scheme the one every other scheme inherits from?

**Source:** JetBrains IDE distributions (proprietary distribution) — study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** Where do shared field validators (hash, version, integer, date…) live so hundreds of event groups don't re-declare them — and what does a registry-only scheme file look like?

## Connected graph-selected seam
**Path/Symbol:** `lib/intellij.pycharm.community.jar:event-log-metadata/IJ_MAP/events-scheme.json` (1,747 bytes, `"version":"5547"`).
**Signature:** `{"groups":[], "rules":{"enums":{...}, "regexps":{...}}, "version":"N"}` — the ONLY family with zero groups; it exists to publish named validators.
**Data Shape:** 17 named regexps (occurrence-exact): count, date_YYYY-MM-DD_HH, date_short_hash, double, float, float_unit, hash, int_pw_of_2, integer, long, long_pw_of_2, negative_integer, negative_long, positive_integer, positive_long, short_hash, version — plus ONE enum table `boolean` = ["true","false","TRUE","FALSE","True","False"] (all six case spellings enumerated because values are compared as strings, not parsed).

### Decisive source
```json
{"groups":[],"rules":{
 "enums":{"boolean":["true","false","TRUE","FALSE","True","False"]},
 "regexps":{"hash":"([0-9A-Fa-f]{40,64})|undefined",
            "short_hash":"([0-9A-Fa-f]{12})|undefined",
            "version":"Unknown|unknown.format|unknown|UNKNOWN|((\\d+\\.?)*\\d+)",
            "count":"\\d+K?M\\+?"}},
 "version":"5547"}
```
(hash/short_hash both end in `|undefined` — absence is an accepted VALUE.)

**Flow:** product schemes reference these names as `{regexp#hash}` / `{enum#boolean}`; FUS additionally extends its OWN top-level rules with product-specific entries beyond the IJ_MAP set (FUS regexps has 21 keys: the 17 shared + kotlin_version, license_metadata, mcu_name, series) — extension-by-superset, never mutation of the shared names.
**Invariant:** the registry's `version` (5547) advances on its own cadence and lags the FUS scheme version (7613) — cross-file references are by NAME with no version pin, so registry entries are append/redefine-compatible only; renaming or tightening a shared regexp silently revalidates every consumer group. The `|unknown` arms encode that telemetry tolerates UNKNOWN over DROP for identity fields.
**Probe:** from `<install>` root:
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/IJ_MAP/events-scheme.json | grep -o '"groups":\[\]' | wc -l` → `1`;
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/IJ_MAP/events-scheme.json | grep -o '"version":"[0-9]*"'` → `"version":"5547"`;
`unzip -p lib/intellij.pycharm.community.jar event-log-metadata/FUS/events-scheme.json | grep -o '"kotlin_version"' | wc -l` → `1` (proving FUS carries registry-plus-extra).
**Coverage caveat:** jar resource plane — not graph-indexed; unzip probes are the retrieval primitive.

## Get live surrounding code
**Retrieve:** no BM25 target (adjudicated wrong-plane). Deterministic retrieval:
`unzip -p <jar> event-log-metadata/IJ_MAP/events-scheme.json | grep -o '"[a-z_0-9]*":' | sort -u` enumerates the validator vocabulary.

**Complements:** fus-events-scheme-grammar (consumer-side union lists); event-log-metadata-family-layout (why a zero-group family exists at all).

## Verdict
Adopt: a named-validator registry scheme shipped beside consumer schemes — shared vocabularies stay name-addressable and append-only. Adapt the primitive types. Omit JetBrains' exact regexes if your identity fields differ; keep the `|unknown` tolerance pattern.
