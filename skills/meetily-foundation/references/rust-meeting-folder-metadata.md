<!-- capsule-v2 -->
# rust-meeting-folder-metadata — how does per-meeting language preference persist outside the database?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the metadata.json contract (fields, atomic write, read precedence) for summary languages?

## Atomic temp-rename JSON beside the meeting folder
**Path/Symbol:** `frontend/src-tauri/src/summary/metadata.rs` (:1-60+).
**Signature:** `pub(crate) fn write_summary_language_to_metadata(folder: &Path, v: Option<&str>) -> Result<()>` (+ detected-language twin pair).
**Data Shape:** One `metadata.json` per meeting `folder_path` with fields `summary_language` and `detected_summary_language` (BCP-47 tags). Missing file ⇒ `Ok(None)` (not an error); missing FIELD inside valid JSON ⇒ None; corrupt JSON ⇒ Err. Writes hold a process-global `METADATA_WRITE_LOCK: Lazy<Mutex<()>>` and go through `.metadata.json.<prefix>` temp files.

### Decisive source
```rust
const SUMMARY_LANGUAGE_FIELD: &str = "summary_language";
const METADATA_FILE: &str = "metadata.json";
const METADATA_TEMP_FILE_PREFIX: &str = ".metadata.json.";
static METADATA_WRITE_LOCK: Lazy<Mutex<()>> = Lazy::new(|| Mutex::new(()));
```

**Flow:** service reads DETECTED language from meeting metadata first (`read_detected_summary_language_from_metadata` via `MeetingsRepository::get_meeting_metadata` → non-empty `folder_path`), falling back to live whatlang detection over the transcript text (`detect_summary_language_from_text`) — so a re-summarize reuses the ORIGINAL detection even after transcript edits.
**Invariant:** Language survives in the FOLDER, not SQLite — deleting the DB row loses it, copying the folder carries it; both reader paths degrade to warn+None rather than failing a summary run.
**Probe:** retrieval-anchored: `search_graph {"query":"read_detected_summary_language_from_metadata"}` resolves `summary/metadata.rs`; battery T16 pins the service-side cache equality this feeds (`cache.source != *expected_source`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "metadata.json summary_language detected write lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt file-beside-data language persistence + temp-rename + global write lock; adapt field names; omit Tauri path resolution. Direct tests absent — behavior pinned via source read + retrieval at pin.
