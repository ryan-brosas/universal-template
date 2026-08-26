<!-- capsule-v2 -->
# Pre/post screenshot VLM verification — how do you prove a browser action worked without trusting the executor's word?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How should before/after screenshots be captured, paired with intent, and analyzed so a vision model can adjudicate whether the action actually executed?

## Opt-in SS_ENABLED gate, class-level analysis history, search-no-change special case
**Path/Symbol:** `core/utils/ss_analysis.py`:`ImageAnalyzer` (`:7-122`, class attr `ss_analysis_history` :9, `analyze_images` :47); gate `core/orchestrator.py:195` + `:384-398/:482-519`; capture `core/browser_manager.py`:`take_screenshots` (`:515-540`).
**Signature:** `ImageAnalyzer(image1_path, image2_path, next_step).analyze_images() -> Dict[str,str]`; `async def take_screenshots(name, page=None, full_page=True, load_state='domcontentloaded', take_snapshot_timeout=15000) -> str|None`.
**Data Shape:** Two PNGs (timestamped `time.time_ns()` prefix) from viewport-only captures around the browser-agent stage; prompt carries the intended `next_step` plus ALL previous analyses as a numbered string. VLM call: base64 data URLs at `detail: high`, max_tokens 2000, separate client/model env pair (`AGENTIC_BROWSER_SS_*`) from the text model.

### Decisive source
```python
await page.wait_for_load_state(state=load_state, timeout=take_snapshot_timeout)
await page.screenshot(path=screenshot_path, full_page=full_page,
                      caret="initial", scale="device")
# ...and the special case baked into the VLM prompt:
# "One special case is that when the action is searching, we are using SERP API
#  so it will be that the webpage does not change at all... The screenshot being
#  unchanged in the case of search is a special case and does not conclude failure"
```
Prompt rules force verdicts over descriptions: state explicitly whether the action succeeded, what appeared/disappeared, whether THIS action broke EARLIER ones (e.g., Enter advancing focus while field one failed), and "confirm and reassure the Critique that if Browser Agent says success, it actually was".
**Flow:** AGENTIC_BROWSER_SS_ENABLED=true gates pre-action capture → BA executes → post-action capture → ImageAnalyzer validates both files exist and open via PIL → base64 encode → VLM diff with history → response appended to CLASS-level history AND into the unified transcript as the ss_analyzer pseudo-tool.
**Invariant:** History is class-level (shared across instances) and cleared only by `clear_history()` in reset_state — forgetting that reset leaks cross-task context into analyses. Screenshot failure here is FATAL (raises CustomException) unlike most browser errors, because acting blind invalidates every downstream critique. The unchanged-page-on-search carve-out prevents the analyzer from misreporting API-driven actions as failures.
**Probe:** No tests (coverage caveat). Graph pins: `trace_path --function-name analyze_images --direction inbound` → Orchestrator.run ss-analysis block; take_screenshots called twice per iteration (Pre_Action_SS/Post_Action_SS).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "ImageAnalyzer analyze_images screenshot", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt opt-in pre/post capture with intent-carrying VLM diffing and the no-change special cases relevant to your tools. Adapt detail level/capture region. Omit PIL validation if your captures are guaranteed fresh writes — but keep fatal-on-failure semantics; silent nulls would starve the critic.
