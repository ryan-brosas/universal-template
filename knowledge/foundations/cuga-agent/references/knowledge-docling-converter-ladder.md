<!-- capsule-v2 -->
# Docling converter cache + orphan clusters + forced OCR — why is create_orphan_clusters load-bearing, when does accurate degrade to balanced, and what is cached per key?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you build/caches a Docling DocumentConverter across mode toggles, and which pipeline flags prevent silent content loss?

## Converter cached per (pdf_mode | effective_layout_engine); OCR three-tier fallback; enrichments always off
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:4796-5054` (`_get_docling_converter`), `_resolve_layout` :4772-4794, layout/OCR probes in `tests/unit/test_knowledge_ocr_language_detect.py`.
**Signature:** `def _get_docling_converter(self) -> DocumentConverter`; `@staticmethod _resolve_layout(layout_engine_choice, device_label) -> (effective_engine, layout_device)`.
**Data Shape:** modes fast/balanced/accurate (unknown → accurate); auto layout: mps/cuda → transformers (GPU honored), cpu → onnx (CPU-only engine), explicit choices are escape hatches; cache_key = `f"{mode}|{effective}"` so explicit-transformers and auto-on-GPU share one entry.

### Decisive source
```python
# engine.py:4895-4912 and :4935-4958
# ``create_orphan_clusters=True`` is LOAD-BEARING. Docling's default
# ``LayoutOptions`` ships with this on; the alternative
# ``LayoutObjectDetectionOptions`` we use here defaults it to OFF ...
# Without it, layout boxes that the object-detection model didn't
# classify into a structure get DROPPED -- observed on a Hebrew
# population-registry form where the field-label column and the actual
# ID number lived in "orphan" text elements. Reproducer: without this
# flag the chunk text collapses from 574 chars to 320 chars and the ID
# is gone.
pipeline_options.layout_options = LayoutObjectDetectionOptions(
    engine_options=engine_opts, create_orphan_clusters=True)
...
# ``force_full_page_ocr=True`` (accurate only) re-OCRs even when a text
# layer exists: some PDFs carry a layer that is font CID glyph IDs with
# no Unicode map -- Docling extracts /CE3/CE5/... mojibake verbatim.
if mode == "accurate":
    if _shutil.which("tesseract"):
        pipeline_options.ocr_options = TesseractCliOcrOptions(lang=["auto"], force_full_page_ocr=True)
```
OCR ladder (:4919-4994): tesseract on PATH (`lang=["auto"]` per-page script detection) → EasyOCR importable (`use_gpu=None if use_gpu else False`, honors opt-out) → NEITHER: effective_mode degrades to "balanced" — never crash ingest. MPS quirk: transformers engine sets `compile_model=device_label != "mps"` because PyTorch 2.11 Inductor MPS codegen crashes shader compilation on layout models. Enrichments stay off everywhere (measured ~20+ min added per 38-page paper). fast mode skips page/picture image rendering via best-effort setattr (Docling surface drift tolerated); unknown attrs never fatal.

**Flow:** resolve mode+layout → cache hit? return → build PdfPipelineOptions(artifacts_path from env) → accelerator options → fast-mode image-render skip → layout options w/ orphan clusters + engine-specific compile flag → OCR tier selection (accurate only) → per-mode overrides → DocumentConverter(PDF format option) → cache + log full effective config.
**Invariant:** Converter caching must key on EFFECTIVE config (mode|resolved-engine) or runtime GPU toggles silently reuse stale weights; defaults must preserve unclassified layout elements (orphan clusters ON) and re-OCR CID-mojibake text layers in quality mode; every degradation (easyocr→balanced, unknown mode→accurate) logs loudly but never raises into ingest.

**Probe:** `tests/unit/test_knowledge_ocr_language_detect.py` — tesseract-auto :23, easyocr fallback :53, balanced degradation :92, enrichments-off-in-every-mode :149, layout auto mps/cuda → transformers :268/:278.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_get_docling_converter _resolve_layout create_orphan_clusters force_full_page_ocr", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: effective-config cache keys, loud-but-never-fatal degradation ladders, orphan-cluster preservation, forced-OCR rationale for CID-corrupt corpora. Adapt engines to your OCR stack. Omit enrichment plumbing (kept off by measured cost). Direct tests pin the OCR/layout ladder.
