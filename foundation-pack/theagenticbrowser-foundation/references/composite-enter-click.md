<!-- capsule-v2 -->
# Composite enter-then-press skill — when is a two-action combo one tool call, and how does it report partial failure?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How do you give an agent a text+submit compound tool that degrades correctly when the selectors are equal or the first half fails?

## Same-selector ⇒ Enter instead of click; success-prefix gate before proceeding
**Path/Symbol:** `core/skills/enter_text_and_click.py`:`enter_text_and_click` (whole file, 81L); reuses `do_entertext` (enter_text_using_selector), `do_click` (click_using_selector), `do_press_key_combination`.
**Signature:** `async def enter_text_and_click(text_selector, text_to_enter, click_selector, wait_before_click_execution: float = 0.0) -> str`.
**Data Shape:** Returns detailed_message string; early-returns a failure message when text entry didn't start with "Success". NOT registered as a BA tool in this fork (imported but unused by browser_agent) — kept as the canonical composite pattern from upstream.

### Decisive source
```python
text_entry_result = await do_entertext(page, text_selector, text_to_enter, use_keyboard_fill=True)
if not text_entry_result["summary_message"].startswith("Success"):
    return f"Failed to enter text '{text_to_enter}' into element with selector '{text_selector}'..."

if text_selector == click_selector:
    ok = await do_press_key_combination(browser_manager, page, "Enter")
    result["detailed_message"] += (' Instead of click, pressed the Enter key successfully...'
                                   if ok else ' ...Tried pressing the Enter key... and failed.')
else:
    do_click_result = await do_click(page, click_selector, wait_before_click_execution)
    result["detailed_message"] += f' {do_click_result["detailed_message"]}'
```
**Flow:** highlight text field → keyboard-fill entry → gate on Success prefix → same selector? press Enter : highlight + click target → 100 ms mutation drain → end screenshot.
**Invariant:** The success-prefix string check is the contract between skill layers — `summary_message` is a STABLE protocol field ("Success. Text … set successfully"), not prose. Submitting a form by clicking inside the field you just filled loses focus state on many sites; pressing Enter is both cheaper and semantically correct, which is why equality routes to the keypress. Search-field rule in the system prompt (:57: "Strictly for search fields, submit the field by pressing Enter") mirrors this at prompt level.
**Probe:** No tests (coverage caveat — pattern-preservation capsule). Graph pin: `trace_path --function-name enter_text_and_click --direction outbound` resolves all three reused primitives, confirming composition-over-reimplementation. Its only in-tree mention is a commented-out import (`browser_agent.py:9`) — the composite is dormant in this fork, kept from upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "enter text and click press enter", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the composite-skill shape and the Enter-on-same-selector rule for any fill+submit surface. Adapt the success sentinel to your own result protocol (or use typed results). Omit registering it as a separate LLM tool when your planner already emits atomic steps.
