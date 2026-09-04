<!-- capsule-v2 -->
# Grounding funnel — how does a natural-language click target become verified pixel coordinates?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How are clicks routed through a dedicated grounding model, and why must every click re-screenshot first?

## click_element base method shared by all three click verbs
**Path/Symbol:** `os_computer_use/sandbox_agent.py:118-150` (`click_element`, `click`, `double_click`, `right_click`); `os_computer_use/osatlas_provider.py:23-33` (`OSAtlasProvider.call`); `os_computer_use/grounding.py:13-22` (`extract_bbox_midpoint`), `:5-10` (`draw_big_dot`).
**Signature:** `click_element(self, query, click_command, action_name="click")`; `grounding_model.call(query, image_path) -> (x, y) | None`.
**Data Shape:** `query` is free text from the LLM ("the search box"); position is a 2-tuple of ints; `None` is the documented under-specified return (2 or ≥4 numbers accepted, anything else rejected).

### Decisive source
```python
def click_element(self, query, click_command, action_name="click"):
    self.screenshot()
    position = grounding_model.call(query, self.latest_screenshot)
    dot_image = draw_big_dot(Image.open(self.latest_screenshot), position)
    filepath = self.save_image(dot_image, "location")
    logger.log(f"{action_name} {filepath})", "gray")
    x, y = position
    self.sandbox.move_mouse(x, y)
    click_command()
```
```python
def extract_bbox_midpoint(bbox_response):
    match = re.search(r"<\|box_start\|>(.*?)<\|box_end\|>", bbox_response)
    inner_text = match.group(1) if match else bbox_response
    numbers = [float(num) for num in re.findall(r"\d+\.\d+|\d+", inner_text)]
    if len(numbers) == 2:
        return numbers[0], numbers[1]
    elif len(numbers) >= 4:
        return (numbers[0] + numbers[2]) // 2, (numbers[1] + numbers[3]) // 2
    else:
        return None
```

**Flow:** fresh screenshot → grounding model returns OS-Atlas bbox token stream → regex strips `<|box_start|>…<|box_end|>` wrapper (falls back to raw text) → float extraction accepts either a bare point (2 nums) or a box (≥4 → integer midpoint via `//2`) → red debug dot stamped on the screenshot → `move_mouse(x,y)` then the caller-supplied click closure.
**Invariant:** Click coordinates are ALWAYS derived from a screenshot taken in the same call — never from `latest_screenshot` staleness across turns — and the annotated image is persisted as evidence BEFORE the click fires. Midpoint uses floor division on floats (returns ints because operands are whole-pixel floats); `< 2` or `3` numbers yield `None`, which will crash the unpacking — under-specified targets fail loudly rather than clicking blind.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && python3 -c "
from os_computer_use.grounding import extract_bbox_midpoint
assert extract_bbox_midpoint('<|box_start|>100.0 200.0 300.0 400.0<|box_end|>') == (200, 300)
assert extract_bbox_midpoint('512 384') == (512.0, 384.0)
assert extract_bbox_midpoint('no coords here') is None
print('grounding funnel OK')"`
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "click_element grounding move_mouse draw_big_dot bbox", limit: 8, fields: ["signature", "name", "file"] });
// expect SandboxAgent.click_element / OSAtlasProvider.call / extract_bbox_midpoint
```

## Verdict
Adopt the same-call screenshot→ground→verify-dot→act ladder for any GUI agent (staleness is THE bug class here); adapt the bbox grammar to your grounder's token format (ShowUI variant below differs deliberately); omit the None-crash behavior by adding explicit handling if you port this into production.
