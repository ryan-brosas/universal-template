<!-- capsule-v2 -->
# Yandex neuro-answer exclusion — why must an AI answer card be skipped from the organic result stream but kept as a feature?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How does the parser stop a generative answer block from stealing rank #1?

## Skip-but-capture
**Path/Symbol:** `yandex/parse_html.go` — `isYandexNeuroAnswer` L123–128, skip call site L41–47; feature spec `yandex/features.go:11–25` (AI-summary SerpFeatureSelector); attachment via `core.AttachFeaturesToFirstResult` (`core/feature_selectors.go:145`).
**Signature:** `isYandexNeuroAnswer(item *goquery.Selection) bool`; container list `"li[data-fast-name='neuro_answer']", ".FuturisSearch", ".FuturisSearchCard"`.
**Data Shape:** the neuro/AI card renders as a `serp-item` li (same wrapper as organic rows) with `data-fast-name="neuro_answer"` on itself or a descendant; its body hydrates client-side from data-state JSON, so static snapshots expose teaser text + source links only.

### Decisive source
```go
// yandex/parse_html.go:41-47 — inside parseYandexDocument's Each()
// The neuro/AI answer renders as a serp-item li too, so it would be
// caught here as an organic row. It is surfaced separately as an
// ai_summary serp_feature; skip it from the rankable result stream.
if isYandexNeuroAnswer(item) {
    return
}
// :123-128 — self OR descendant carries the marker
if name, ok := item.Attr("data-fast-name"); ok && name == "neuro_answer" { return true }
return item.Find("[data-fast-name='neuro_answer']").Length() > 0
```
Feature side (`features.go`): Type `ResultTypeAISummary`, Title "Нейро", Position 1, Confidence 0.6; text from `.FuturisGPTMessage-GroupContent`/`.FuturisSearchCard-Content`/`.FuturisSnippetText`; citations restricted to `a.FuturisSource[href^='http']` + `.FuturisSourceDetails a[href^='http']` — in-source comment: "Restrict to cited sources; the block also contains reasoning-plan chips and follow-up suggestion links we don't want as citations."
**Flow:** parseYandexDocument ends with `AttachFeaturesToFirstResult(DeduplicateResults(results), extractYandexFeatures(doc))` — features ride the first RESULT row (or standalone when zero rows), never occupy a Rank slot.
**Invariant:** one DOM node, two output channels: excluded from ranks (would otherwise be Rank 1 and shift every organic result), included as `ai_summary` feature with its own confidence. Citation selectors are allowlisted because the card's interactive chrome (chips, follow-ups) would otherwise leak in as fake citations.
**Probe:** fixture-level coverage via `yandex/parse_html_test.go:10 TestParseYandexHTML` (rank sequence integrity); serp-feature extraction pinned by `core/serp_features_test.go`.
**Python-equivalent probes (executed byte-exact):**
```bash
grep -n 'data-fast-name' yandex/parse_html.go | head -3   # → :45 comment, :124 attr check, :127 descendant find
```
```python
rows = [{"fast": None}, {"fast": "neuro_answer"}, {"fast": None}]
def is_neuro(r): return r["fast"] == "neuro_answer"
organic = [i for i, r in enumerate(rows) if not is_neuro(r)]
assert [r.get("rank") for i, r in enumerate(rows) if not is_neuro(r)] == organic  # ranks 1..2, gap-free
print("neuro-answer exclusion GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "isYandexNeuroAnswer neuro_answer FuturisSearch extractYandexFeatures", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt skip-from-ranks/capture-as-feature for every engine's AI-answer block (the same shape exists across SERPs under different markup). Adapt marker attributes and citation allowlists per engine.
