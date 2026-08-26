<!-- capsule-v2 -->
# Applied-jobs CSV→JSON remap — how do I expose a flat bot-written CSV as a JSON API and stamp rows without corrupting it?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** How does a control panel read the bot's append-only CSV ledger, present it as JSON with API-safe keys, and mark one row applied — while preserving the CSV for the dedupe consumer?

## Column remap + PUT stamping
**Path/Symbol:** `app.py:_HISTORY_FIELDS` (:237–245) + `/applied-jobs` GET (:248–261) + `/applied-jobs/<job_id>` PUT (:264–289).
**Signature:** `GET /applied-jobs -> [{Job_ID, Title, Company, HR_Name, HR_Link, Job_Link, External_Job_link, Date_Applied}]`; `PUT /applied-jobs/<job_id> -> 200|404`.
**Data Shape:** source CSV columns are space-laden (`'Job ID'`, `'Date Applied'`, `'External Job link'`) written by the append-only DictWriter ledger (see ledger-contrast-csv-vs-summary); JSON keys replace spaces with underscores.

### Decisive source
```python
COLUMN_MAPPING = {
    'Job ID': 'Job_ID',
    ...
    'Date Applied': 'Date_Applied',
}

@app.route('/applied-jobs', methods=['GET'])
def get_applied_jobs():
    try:
        with open(os.path.join(PATH, 'all_excels/all_applied_applications_history.csv'), ...) as f:
            return jsonify([
                {COLUMN_MAPPING.get(k, k): v for k, v in row.items()}
                for row in csv.DictReader(f)
            ])
    except FileNotFoundError:
        return jsonify({"error": "No applications history found."}), 404
```

The PUT handler re-opens the same file, walks `csv.DictReader` rows in order, matches `row['Job ID'] == job_id`, sets `row['Date Applied'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')`, then rewrites the whole file via a `csv.DictWriter` over the SAME `_CSV_COLUMNS` fieldnames.
**Flow:** GET = read → per-row dict-comprehension remap (unknown keys pass through untouched) → 404 when no ledger exists. PUT = match-by-job-id → timestamp stamp → full-file rewrite. The bot keeps appending; the panel only mutates the one column it owns.
**Invariant:** the CSV remains the canonical store — JSON is a projection. Rewriting with the identical `fieldnames` list is what keeps the ledger consumable by BOTH consumers (the dedupe set reads raw CSV; the panel reads the remapped projection). Missing-file ⇒ loud 404, never an empty-list lie. Unknown job id on PUT ⇒ 404, not silent success.
**Probe:** `tests/test_app_integration.py::test_applied_jobs_get_maps_columns_to_json_keys`, `::test_applied_jobs_mark_applied_updates_date`, `::test_applied_jobs_missing_file_returns_404`, `::test_applied_jobs_mark_unknown_id_returns_404` (all isolate writes to tmp_path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "applied jobs COLUMN_MAPPING", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit column-remap + whole-file-rewrite-on-stamp pattern whenever a human-facing surface must sit on top of a machine-format ledger. Adapt key-naming rules to your API conventions. Omit the specific columns (product data). Direct tests pin all four behaviors including both 404s.
