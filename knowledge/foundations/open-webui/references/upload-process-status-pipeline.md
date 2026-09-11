<!-- capsule-v2 -->
# Upload→process status pipeline — how does a browser upload become processed content with live progress, and who is allowed to auto-link it?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** What is the contract between the multipart upload endpoint, its background/inline processing bridge, the per-file SSE status stream, and the browser helper that consumes them?

## Upload admission → process bridge → status stream
**Path/Symbol:** `backend/open_webui/routers/files.py:upload_file` (:271–312) → `upload_file_handler` (:315–465) → `process_uploaded_file` (:128–268); status `get_file_process_status` (:611–667); client `src/lib/apis/files/index.ts:uploadFile` (:4–96) + `getFileProcessStatus` (:98–120).
**Signature:** `POST /files/?process=bool&process_in_background=bool` (multipart `file`, optional JSON-string `metadata`) → dict `{'status': True, **file_item}` when processed, else FileModelResponse; `GET /files/{id}/process/status?stream=true` → SSE.
**Data Shape:** DB row gets `data.status='pending'` iff processing; `meta` = {name, content_type, size, file_hash, data:<client metadata>}; SSE frames are `data: {"status": "..."}\n\n` (+`error` on failed).

### Decisive source
```python
            async def event_stream(file_id):
                # NOTE: We intentionally do NOT capture the request's db session here.
                # Each poll creates its own short-lived session to avoid holding a
                # connection for hours. A WebSocket push would be more efficient.
                for _ in range(MAX_FILE_PROCESSING_DURATION):        # 3600 * 2 polls @ sleep(1)
                    file_item = await Files.get_file_by_id(file_id)  # Creates own session
```
```python
                    try:
                        # Gate like POST /knowledge/{id}/file/add: a client-supplied
                        # metadata.knowledge_id must not let a non-writer attach files (CWE-862/863).
```

**Flow:** handler parses string-metadata as JSON (fail ⇒ 400); extension allow-list (`rag.file.allowed_extensions`) applies ONLY when processing; stores blob `{uuid}_{name}` with an ENAMETOOLONG retry that `seek(0)`s and renames to `{id}.{ext}` (:367–384); enforces `rag.file.max_size` AFTER storage, deleting the blob on 413; computes `file_hash` from client value or raw-bytes sha256 ("for incremental sync diffing"); binds `channel_id` owner-checked. Processing topology: BackgroundTask+dict-return when backgrounded, inline await otherwise — the RESPONSE TYPE encodes the mode. The bridge re-labels mislabeled text (`image//video/` bytes passing `_is_text_file` ⇒ `text/plain`, e.g. `.ts` as video/mp2t), routes audio→transcribe→process_file(content=…), marks video completed as-is for multimodal use, else plain process_file; then AUTO-LINK: `metadata.knowledge_id` triggers a server-side mirror of the knowledge add INCLUDING the CWE-862/863 write-access gate (excerpt above), flipping status to `processing` so the generic stream stays open through BOTH vector writes, and RAISES if the model-layer link returns falsy. Status endpoint denies with 404-shape (owner ∨ admin ∨ read grant) and polls fresh-session-per-second up to 2h, emitting terminal frames for completed|failed, breaking silently on legacy no-status rows, `{"status":"not_found"}` for vanished files. Client `uploadFile` defaults `stream=true`: after the multipart POST it pipes the SSE through TextDecoderStream+splitStream('\n'), records mid-stream `data.error` onto `res.error` WITHOUT throwing ([DONE] frames only console.log) — callers must inspect `res.error` themselves.
**Invariant:** the pooled DB connection is never held across polling or embedding (fresh sessions everywhere long work happens); client-supplied routing metadata (knowledge_id) can NEVER bypass the server-side permission gate it mirrors.
**Probe:** `grep -n "A WebSocket push would be more efficient" backend/open_webui/routers/files.py` → 633; `grep -n "(CWE-862/863)" backend/open_webui/routers/files.py` → 208; `grep -n "Detect mis-labeled text files" backend/open_webui/routers/files.py` → 141.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", name_pattern: ".*(upload_file|process_status|get_file_process).*", limit: 20 });
```
(resolves upload_file :272–312, upload_file_handler :315–465, get_file_process_status :612–667.)

## Verdict
Adopt: response-type-encodes-processing-mode; post-storage size enforcement with compensating blob delete; ENAMETOOLONG rename-retry; fresh-session SSE polling ladder; server-side re-gate of any client-supplied linkage metadata. Adapt: poll interval/duration caps; frame schema. Omit: provider-specific Storage tags. Caveat: browser-side extraction twin exists (`src/lib/utils/index.ts extractContentFromFile` :1837–1920 — pdfjs/mammoth/text ladder consumed by MessageInput.svelte :832) but is a separate seam. Zero test files at pin; evidence source+graph only.
