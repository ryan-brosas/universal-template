<!-- capsule-v2 -->
# py-summary-status-code-map — which HTTP status does /get-summary return for each process state, and what shape?

**Source:** meetily (MIT) `main@0281737d`; Codebase Memory `ext-meetily`. **Question:** What is the polling contract a client must implement against `/get-summary/{meeting_id}` (status codes, body fields, error mapping)?

## Status-to-HTTP mapping with data suppression
**Path/Symbol:** `backend/app/main.py:get_summary` (:368-509).
**Signature:** `async def get_summary(meeting_id: str)` → `JSONResponse`.
**Data Shape:** Body always `{status, meetingName, meeting_id, start, end, data}`. `data` is non-null ONLY on `completed`; completed-with-unparseable-result ⇒ 500 `"Completed but summary data is missing or invalid"`. `failed` maps to HTTP 400 with `status="error"` and error text; in-flight (`processing|pending|started` normalized to `processing`) ⇒ HTTP 202; unknown stored status string ⇒ 500.

### Decisive source
```python
response = {
    "status": "processing" if status in ["processing", "pending", "started"] else status,
    ...
    "data": transformed_data if status == "completed" else None
}
if status == "failed":      ... return JSONResponse(status_code=400, content=response)
elif status in [...]:       ... return JSONResponse(status_code=202, content=response)
elif status == "completed":
    if not summary_data:    ... return JSONResponse(status_code=500, ...)
    return JSONResponse(status_code=200, content=response)
```

**Flow:** row join `transcripts ⋈ summary_processes` via `get_transcript_data` (missing row ⇒ 404-shaped JSONResponse with `status:"error"`) → double-`json.loads` guard (result may be stored as JSON-encoded STRING — first parse may yield a str that needs a second parse :394-398) → section transform.
**Invariant:** The frontend transform keys MeetingNotes sections into snake_case dict entries plus a `_section_order` array preserving render order (:437-457); duplicate titles get `_<index>` suffixes. A porter dropping `_section_order` loses section ordering silently.
**Probe:** `grep -c '_section_order' backend/app/main.py` → `3` (battery P4).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meetily", query: "get_summary status processing pending started", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 202/200/400/500 status ladder and double-parse guard; adapt the snake_case transform to your client; omit CORS `allow_origins=["*"]` dev posture. Direct tests absent — coverage caveat recorded.
