<!-- capsule-v2 -->
# Export importer contract — whose names do your output columns carry?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** What belongs in a hand-off file consumed by third-party importers, and which rows must it exclude?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/export.py:RECORD_FIELDS` (:54-65), `lead_record` (:68-91), `lead_records` (:94-122), `export_counts` (:144-157).
**Signature:** `lead_records(campaign) -> Iterable[dict]` (lazy generator over `.iterator()`); `write_csv(records, stream) -> int`.
**Data Shape:** RECORD_FIELDS = email, first_name, last_name, company, title, website, linkedin_url, reason, lead_id, qualified_at — Instantly/Smartlead require the first three and standard-map company/title/website/linkedin_url; anything else becomes a custom variable.

### Decisive source
```python
deals = (
    Deal.objects.filter(campaign=campaign, lead__disqualified=False)
    .exclude(state=DealState.FAILED)          # BOTH rejections are separate columns:
    .select_related("lead", "lead__company")  # FAILED+wrong_fit = LLM's campaign-scoped no,
    .order_by("lead__creation_date")          # Lead.disqualified = permanent account-level opt-out.
)
return (lead_record(deal) for deal in deals.iterator())
# filtering only on `disqualified` shipped once: exported 1,944 rows from a campaign
# where most deals were rejections.
```

**Flow:** deals stream → per-record dict with importer-exact keys → csv.DictWriter(extrasaction="raise") so an extra field crashes instead of silently becoming noise. The CSV is stdout of `find`, not a written file.
**Invariant:** Columns are **the importers', not ours** (`company` not company_name; `title` not job_title) so files import without column mapping; everything we'd like to ship that they don't know is left out rather than dumped as noise variables. There is NO score column deliberately: exporting P(f>0.5) invited thresholding on a number nobody calibrated (the gate decides whether to spend a credit, not whether a lead fits), and computing it made export expensive AND unsafe (warm-start GP fit = O(n³), plus ensure_anchors would make LLM calls and mutate state from a read-only path). `qualified_at` (ISO-8601 UTC seconds) carries provenance because an invocation-relative `new` flag "is a lie the second time it is read" in a file that outlives the invocation. Exportable ≠ mailable: QUALIFIED exports with blank email.
**Probe:** `tests/test_export.py::TestLeadRecords` (:93-141), `TestExportCounts` (:172+), `TestWriters` (:142-171).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "lead_records", limit: 5 });
```

## Verdict
Adopt importer-named columns, exclusion of every rejection class (enumerate them), provenance timestamps over relative flags, lazy streaming writes, and the no-score-column rule. Adapt field lists to your consumers' actual import specs; omit the Instantly/Smartlead specifics if targeting other importers.
