<!-- capsule-v2 -->
# Rebrowser verdict decoding — how does a detector site's JSON payload merge with its rendered table into per-check verdicts?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How does the richest fpcheck detector combine two evidence channels without double-counting?

## JSON + table fusion
**Path/Symbol:** `core/fpcheck/detectors/rebrowser.go` — readiness wait L38–67, extraction JS L72–128, `rebrowserChecksToDetections` L150–192; struct `rebrowserCheck{Type,Icon,Rating,Note,Debug}` L30–36.
**Signature:** `Rebrowser.Extract(ctx, page) (map[string]fpcheck.Detection, string /*rawNotes*/, error)`; `rebrowserChecksToDetections(checks []rebrowserCheck) map[string]fpcheck.Detection`.
**Data Shape:** channel 1: `#detections-json` textarea value = JSON array `[{type,rating,note,debug}]`; channel 2: `#detections-table tbody tr` rows (icon glyph in first cell, note in third). Both funnel into an in-page `Map` keyed by normalized type — LAST WRITE WINS per key via the `put()` merge (empty fields never clobber non-empty current).

### Decisive source
```js
// rebrowser.go:85-93 — merge semantics inside put()
const current = checks.get(type) || { type, icon: "", rating: 0, note: "", debug: "" };
const next = {
    type,
    icon:   normalize(item.icon || current.icon),     // falsy keeps existing
    rating: Number.isFinite(item.rating) ? item.rating : current.rating,
    note:   normalize(item.note || current.note),
    debug:  normalize(item.debug || current.debug),
};
checks.set(type, next);
```
Go-side verdict ladder (:158–166): `"🔴"` ⇒ detected; `"🟢","🟡","⚪️","⚪"` ⇒ clean; ANY other icon ⇒ `detected = check.Rating >= 1` — rating is the tiebreaker when glyphs are missing. Description = Note, then `Note | Debug` when both present, then fallback `rating=%.2f`. Every detected row gets Severity "critical"; `unknown` keys skipped.
**Flow:** readiness = poll until the JSON textarea parses to a NON-empty array (`waitFor` 20s/250ms) before either channel is read; empty checks array OR empty detections map are hard errors ("rebrowser detections are empty").
**Invariant:** two-channel union keyed by type means table-only and JSON-only checks BOTH survive; the in-page merge guarantees one entry per check type regardless of how many sources mention it. Raw notes returned to the caller are the marshaled checks JSON (audit trail), not prose.
**Probe:** `core/fpcheck/detectors/rebrowser_test.go` pins the mapping logic offline; live site is integration-only.
**Python-equivalent probe (executed byte-exact):**
```bash
grep -n '"🔴"\|"🟢"\|Rating >= 1' core/fpcheck/detectors/rebrowser.go   # → :160/:162/:165
```
```python
def detected(icon, rating):
    if icon == "🔴": return True
    if icon in ("🟢", "🟡", "⚪️", "⚪"): return False
    return rating >= 1                      # unknown icon: rating decides
assert detected("🔴", 0) and not detected("🟢", 5) and detected("", 1.0) and not detected("", 0.9)
print("rebrowser verdict ladder GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "rebrowserChecksToDetections detections-json rebrowser Extract", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt last-write-wins keyed merging for multi-channel scrapes of the same entities; keep the emoji→rating fallback so verdicts degrade gracefully when markup changes. Adapt keys/vocab to your own detector fleet.
