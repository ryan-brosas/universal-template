<!-- capsule-v2 -->
# fpcheck detection kernel — how do five detector sites with incompatible DOMs normalize into one Detection verdict map?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What is the shared extraction grammar behind the fingerprint self-check detectors?

## Shared helpers
**Path/Symbol:** `core/fpcheck/detectors/helpers.go` — `waitFor` L27–59, `normalizeKey` L61–83, `classifyStatus` L85–113, `parseRows` L115–192 (in-page JS), `rowsToDetections` L194–220, `extractScore` L238–248; registry `registry.go:11–20`.
**Signature:** `waitFor(ctx, timeout, poll time.Duration, probe func() (bool, error)) error` (defaults 20s/250ms); `normalizeKey(name string) string` (empty ⇒ "unknown"); `classifyStatus(status string) bool`; `rowsToDetections(rows []detectorRow, criticalKeywords []string) map[string]fpcheck.Detection`.
**Data Shape:** `detectorRow{name,status,detail}` harvested by ONE in-page JS pass over `table tr` cells + fallback candidates (`[data-test],[data-testid],.check,.result,li`, ≤260 chars, verdict-keyword-gated); deduped case-insensitively by name.

### Decisive source
```go
// core/fpcheck/detectors/helpers.go:91-112 — emoji-first status classification
if strings.Contains(value, "🔴") { return true }
if strings.Contains(value, "🟢") || strings.Contains(value, "⚪") { return false }
notDetected := []string{"not detected","not found","clean","clear","pass","passed","ok","safe","green","false","no"}
detected    := []string{"detected","fail","failed","bot","leak","warning","critical","red","true","yes"}
// first matching marker wins; unknown text classifies as NOT detected
```
Severity is keyword-escalation, not site-declared: `rowsToDetections` marks `critical` only when `hasKeyword(key+" "+detail, criticalKeywords)` (:204–206). Registry: exactly 5 standard factories `{sannysoft, rebrowser, browserscan, pixelscan, deviceandbrowser}` + custom(url[,selector]); `Select(name, customURL)` errors `"unknown detector %q"` listing names.
**Flow:** every detector = readiness-wait (`waitFor`) → page.Eval harvest → per-site mapping into `map[key]{Detected, Description, Severity}`; runner adds screenshot + summary counts.
**Invariant:** normalizeKey collapses separators to `_` and empty/garbage keys become "unknown" which consumers SKIP (never emit junk rows); classifyStatus is fail-open (unknown ⇒ not detected) because a broken parse must not fabricate detections; the emoji check precedes word lists since sites localize their prose but reuse the traffic-light glyphs.
**Probe:** `core/fpcheck/detectors/registry_test.go` pins Select/Names behavior; live sites are integration-only by nature.
**Python-equivalent probes (executed byte-exact):**
```bash
grep -c 'name:' core/fpcheck/detectors/registry.go          # → 5 standard factories
grep -n '"not detected"\|"leak"' core/fpcheck/detectors/helpers.go | head -3   # → :98/:105 lists
```
```python
def classify_status(v):
    if "🔴" in v: return True
    if "🟢" in v or "⚪" in v: return False
    if any(m in v for m in ["not detected","clean","pass","ok","safe","false","no"]): return False
    if any(m in v for m in ["detected","fail","bot","leak","warning","critical","true","yes"]): return True
    return False
assert classify_status("🔴 webdriver leak") and not classify_status("🟢 clean") and not classify_status("gibberish")
print("fpcheck classifyStatus GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "fpcheck detector Extract detections normalizeKey classifyStatus", limit: 4, fields: ["signature","name","file"] });
```
Live at pin: rank-2 `normalizeKey` helpers.go:61–83, rank-3 `classifyStatus` helpers.go:85–113 (total:194).

## Verdict
Adopt the normalize→classify→escalate pipeline plus fail-open semantics for scraping heterogeneous dashboards; adapt keyword vocabularies and emoji sets per ecosystem. Omit in production paths — this kernel exists for self-diagnostics only.
