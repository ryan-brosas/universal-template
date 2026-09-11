<!-- capsule-v2 -->
# Grounding provider SPI — how do two vision grounder models with different output grammars share one call site?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** What is the minimal contract a grounding model must satisfy, and how do OS-Atlas and ShowUI differ behind it?

## Duck-typed call(prompt, image) -> (x,y)|None; parsing lives INSIDE each provider
**Path/Symbol:** `os_computer_use/osatlas_provider.py:15-33` (`OSAtlasProvider`); `os_computer_use/showui_provider.py:10-42` (`ShowUIProvider`, incl. its latent bug); swap point `os_computer_use/config.py:5-6`.
**Signature:** `call(self, prompt, image_data) -> (x, y) | None` — the entire SPI.
**Data Shape:** OS-Atlas: gradio Space `maxiw/OS-ATLAS`, api `/run_example`, result[1] = bbox token string, appends "\nReturn the response in the form of a bbox" to every prompt. ShowUI: Space `showlab/ShowUI`, api `/on_submit`, result[1] = python-literal NORMALIZED coordinates.

### Decisive source
```python
# OS-Atlas path: token-stream → midpoint (see grounding funnel capsule)
result = self.client.predict(image=handle_file(image_data),
                             text_input=prompt + "\nReturn the response in the form of a bbox",
                             model_id=OSATLAS_HUGGINGFACE_MODEL,
                             api_name=OSATLAS_HUGGINGFACE_API)
position = extract_bbox_midpoint(result[1])
```
```python
# ShowUI path: normalized 0..1 pair scaled by image dims
point = ast.literal_eval(response)
if len(point) == 2:
    x, y = point[0] * image.width, point[1] * image.height
    return x, y
else:
    return None
```

**Flow:** config.py binds ONE module-global (`grounding_model = providers.OSAtlasProvider()`; ShowUI commented as drop-in) → click_element calls `.call(query, screenshot_path)` blindly → each provider owns: Space endpoint constants, request param names, response grammar parse, and coordinate normalization (absolute-midpoint vs relative-scale).
**Invariant:** The agent loop never knows which grounder runs — swapping vendors is one line in config.py. ShowUI's `extract_norm_point` carries a LATENT BUG worth porting knowledge: it references bare `np` (never imported) on the array branch, and downloads the ANNOTATED image just to read dimensions — adopters should open the local file instead. HF_TOKEN is captured at import time like all other keys.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && grep -n 'def call' os_computer_use/osatlas_provider.py os_computer_use/showui_provider.py && grep -n 'grounding_model' os_computer_use/config.py` (pins identical signatures and the single swap point).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "OSAtlasProvider ShowUIProvider gradio predict handle_file", limit: 8, fields: ["signature", "name", "file"] });
// expect both provider classes + their predict payloads
```

## Verdict
Adopt the one-method grounding SPI with vendor-owned parsing for any GUI-agent stack; adapt normalization per model output grammar (absolute vs relative coords is THE fork); omit the remote-image-dimension fetch (port ShowUI against local files).
