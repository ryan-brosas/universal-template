<!-- capsule-v2 -->
# Five-Fragment Document Masking — how does client-side fragmentation prove the full document never leaves the machine?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What mask geometry, format, and upload protocol preserve both the privacy claim AND reviewer legibility?

## ≤50%-per-mask geometry + lossless PNG + DEK-forggetting upload
**Path/Symbol:** `packages/python/awaithumans/awaitverify/fragmentation.py` — `load_pages` (:81–132), `fragment_document/_fragment_page/_mask_regions` (:134–195); orchestration `awaitverify/client.py:verify_document` (:140–330); crypto `awaitverify/_encryption.py:encrypt_fragment`.
**Signature:** `fragment_document(source) -> list[list[bytes]]` — outer = pages, inner = exactly AWAITVERIFY_FRAGMENT_COUNT(5) PNGs.
**Data Shape:** masks in (l,t,r,b): right-half, left-half, center-strip(q→3q), top-half, bottom-half; PDFs rasterized at 300 DPI; office formats via LibreOffice headless→PDF (ZIP `PK\x03\x04` / OLE magic sniff).

### Decisive source
```python
return [
    (half_w, 0, width, height),            # 0: hide right half
    (0, 0, half_w, height),                # 1: hide left half  (was three_quarter_w → asymmetric)
    (quarter_w, 0, three_quarter_w, height),  # 2: hide center 50%
    (0, 0, width, half_h),                 # 3: hide top half
    (0, half_h, width, height),            # 4: hide bottom half
]
```
Upload pipeline:
```python
session = await _managed_create_upload_session(...)   # mints DEK + per-slot signed URLs
for page_index, frags in enumerate(page_fragments):
    for fragment_index, plaintext in enumerate(frags):
        slot = slot_by_key.get((page_index, fragment_index))   # index-verified against backend
        ciphertext = encrypt_fragment(plaintext, session.dek)  # nonce(12)||GCM ct||tag
        tasks.append(_bounded_upload(slot, ciphertext))         # Semaphore(8)
upload_session_id = session.upload_session_id   # SDK forgets the plaintext DEK NOW
```

**Flow:** load locally (Pillow multi-frame loop; office via temp-dir LibreOffice subprocess with FileNotFoundError/Timeout/CalledProcessError each mapped to typed VerifyDocumentLoadError + install hints) → five black-boxed copies per page saved PNG compress_level=1 (lossless so masks add no JPEG generation loss; source resolution preserved) → POST /uploads for DEK+signed URLs → encrypt+PUT bounded by Semaphore(AWAITVERIFY_UPLOAD_CONCURRENCY=8) (50 simultaneous TLS PUTs melt residential uplinks; 300s per-PUT timeout for 5 Mbps uplinks) → forget DEK (server holds only wrapped form, destroyed on reviewer submit ⇒ fragments permanently undecryptable) → POST /tasks → poll.
**Invariant:** every mask blacks out AT MOST 50% (reviewer reassembles by scanning fragments — asymmetric masks make carousels lopsided; test tightened from ≤75% specifically so asymmetry can't sneak back). Page cap 100 raises VerifyDocumentTooLargeError.
**Probe:** `tests/awaitverify/test_fragmentation.py` (:45–136 exact-five, per-region coordinates, partition-height, **no-region->50%**, mirror-image pairs; :139–170 PNG bytes/black-region/too-many-pages).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "fragment_document mask regions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt symmetric ≤50% masking, lossless fragment encoding, semaphore-bounded encrypted uploads, explicit DEK forgetting, and magic-byte format routing. Adapt fragment count/DPI to your review surface. Omit Azure Blob specifics of _managed_client.
