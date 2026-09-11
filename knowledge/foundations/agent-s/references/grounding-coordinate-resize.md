<!-- capsule-v2 -->
# grounding-coordinate-resize — How does a natural-language element description become screen coordinates?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How are grounding-model outputs parsed and rescaled, and what does the parse tolerate?

## Coordinate seam
**Path/Symbol:** `gui_agents/s3/agents/grounding.py:OSWorldACI.generate_coords` (:230-246) + `resize_coordinates` (:337-344); consumption in click (:361-362), type (:440-441), drag_and_drop (:484-487), scroll (:613-614).
**Signature:** `generate_coords(ref_expr: str, obs) -> List[int]`; `resize_coordinates(coordinates) -> List[int]`.
**Data Shape:** Grounding engine params MUST carry `grounding_width`/`grounding_height` (the model's native coordinate space, e.g. UI-TARS). Output = `[x*screen_w/gw, y*screen_h/gh]` rounded. Screenshot is downscaled to max-dim 2400 upstream (cli_app.py :326-330 `scale_screen_dimensions`).

### Decisive source
```python
# generate_coords — parse ALL digit runs, take the first two
response = call_llm_safe(self.grounding_model)
numericals = re.findall(r"\d+", response)
assert len(numericals) >= 2
return [int(numericals[0]), int(numericals[1])]

# resize_coordinates
grounding_width = self.engine_params_for_grounding["grounding_width"]
grounding_height = self.engine_params_for_grounding["grounding_height"]
return [round(coordinates[0] * self.width / grounding_width),
        round(coordinates[1] * self.height / grounding_height)]
```

**Flow:** per call the grounding LMMAgent is RESET (stateless one-shot :233), prompt puts TEXT FIRST then image (`put_text_last=True` moves text after the image part — UI-TARS demo convention, :236-239) → response parsed for raw digit runs → first two become (x,y) in model space → resize into real screen space → caller embeds into a pyautogui string.
**Invariant:** (1) The regex takes the FIRST two numbers anywhere in the response — verbose models that echo indices before coordinates corrupt clicks; prompt wording ("Output only the coordinate of one point") is load-bearing. (2) No clamping to screen bounds at this layer. (3) The grounding agent keeps NO conversation history across calls (reset each time) — every click is an independent VQA query. (4) put_text_last exists because UI-TARS expects image-before-text part ordering; other engines ignore it.
**Probe:** `grep -n 'int(numericals\[0\]), int(numericals\[1\])' gui_agents/s3/agents/grounding.py` → :246.
**Probe:** `grep -n 'put_text_last=True' gui_agents/s3/agents/grounding.py` → :238.
**Probe:** `grep -n 'round(coordinates\[0\] \* self.width / grounding_width)' gui_agents/s3/agents/grounding.py` → :342.
**Probe:** `grep -n 'max_dim_size=2400' gui_agents/s3/cli_app.py` → :329.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "generate_coords resize_coordinates grounding", limit: 5 });
```

## Verdict
Adopt stateless grounding calls with explicit two-space coordinate algebra and defensive digit parsing; adapt the parser to your model's output contract; omit nothing — the width/height params being REQUIRED config (KeyError if absent) is intentional.
