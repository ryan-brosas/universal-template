<!-- capsule-v2 -->
# text-span-alignment-coords — How does a phrase map to a selection edge for highlight operations?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How does OCR word-index grounding work, and how do start/end alignments pick opposite edges of a word?

## Text-span seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:OSWorldACI.get_ocr_elements` (:249-283) + `generate_text_coords` (:286-327); consumed by `highlight_text_span` (:504-525).
**Signature:** `get_ocr_elements(b64_image_data) -> Tuple[str, List[dict]]`; `generate_text_coords(phrase, obs, alignment="") -> List[int]`.
**Data Shape:** OCR element = `{id, text, group_num, word_num, left, top, width, height}` (pytesseract block grouping; ids are COMPACTED — only non-empty words get an id). ocr_table renders "Word id\tText" lines fed to the LLM. alignment ∈ {"start", "end", ""}.

### Decisive source
```python
# word-id resolution: LAST number in the response, 0 on none
numericals = re.findall(r"\d+", response)
text_id = int(numericals[-1]) if numericals else 0
elem = ocr_elements[text_id]

if alignment == "start":
    coords = [elem["left"], elem["top"] + elem["height"] // 2]           # LEFT edge midline
elif alignment == "end":
    coords = [elem["left"] + elem["width"], elem["top"] + elem["height"] // 2]  # RIGHT edge midline
else:
    coords = [elem["left"] + elem["width"] // 2, elem["top"] + elem["height"] // 2]
```

**Flow:** screenshot → pytesseract image_to_data → strip non-alphabet edges from words → compact id assignment in scan order with per-block word numbering → table+phrase+alignment prompt to text_span_agent (PHRASE_TO_WORD_COORDS_PROMPT) → LLM returns a word id → element box converted to an EDGE-anchored point → highlight action drags moveTo(start)→dragTo(end).
**Invariant:** (1) Start picks the LEFT edge, end picks the RIGHT edge of the respective words — both at vertical midline; using centers would miss the first/last characters when dragging. (2) The id lookup indexes the COMPACTED list (`ocr_elements[text_id]`), so any off-by-one between the rendered table and the list breaks silently onto the wrong word — the table and list MUST be built by the same loop (:264-281). (3) No numeric response degrades to word 0 rather than failing. (4) These coordinates are NOT passed through resize_coordinates — they come from the SAME screenshot pixels the drag executes on (highlight_text_span uses them raw, :517-518).
**Probe:** `grep -n 'int(numericals\[-1\])' gui_agents/s3/agents/grounding.py` → :312.
**Probe:** `grep -n 'elem\["left"\] + elem\["width"\]' gui_agents/s3/agents/grounding.py` → :321.
**Probe:** `grep -n 'alignment == "start"' gui_agents/s3/agents/grounding.py` → :293 (prompt arm) and :318 (coord arm).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "generate_text_coords get_ocr_elements alignment", limit: 5 });
```

## Verdict
Adopt OCR-table word-id grounding with edge-aligned coordinates for spans; adapt the OCR engine and prompt; omit nothing — the same-loop table/list construction and the no-resize raw-pixel contract are the traps.
