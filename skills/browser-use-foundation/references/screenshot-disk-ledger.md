<!-- capsule-v2 -->
# Screenshot disk ledger — how do you keep per-step screenshots available for replay without holding image bytes in agent memory or telemetry?

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** where do base64 screenshots live during a long agent run so history stays small, GIF/eval consumers can still fetch pixels, and observability spans never capture image bytes?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/screenshots/service.py` whole (52L) — `ScreenshotService.__init__` (:16-22), `store_screenshot` (:25-36), `get_screenshot` (:39-52). Consumers (trace-confirmed): `Agent._make_history_item`, `Agent._finalize`, beta twins. Wiring pinned by `tests/ci/test_beta_agent.py:5508-5536`.
**Signature:** `async store_screenshot(screenshot_b64: str, step_number: int) -> str`; `async get_screenshot(screenshot_path: str) -> str | None`.
**Data Shape:** disk layout `<agent_directory>/screenshots/step_{n}.png`; history items store ONLY the path string; bytes re-enter memory lazily as base64 on demand.

### Decisive source
```python
# __init__ — directory created eagerly at agent setup
self.screenshots_dir = self.agent_directory / 'screenshots'
self.screenshots_dir.mkdir(parents=True, exist_ok=True)

@observe_debug(ignore_input=True, ignore_output=True, name='store_screenshot')
async def store_screenshot(self, screenshot_b64: str, step_number: int) -> str:
    screenshot_filename = f'step_{step_number}.png'
    screenshot_path = self.screenshots_dir / screenshot_filename
    screenshot_data = base64.b64decode(screenshot_b64)
    async with await anyio.open_file(screenshot_path, 'wb') as f:
        await f.write(screenshot_data)
    return str(screenshot_path)          # ONLY the path travels onward

@observe_debug(ignore_input=True, ignore_output=True, name='get_screenshot_from_disk')
async def get_screenshot(self, screenshot_path: str) -> str | None:
    if not screenshot_path: return None
    path = Path(screenshot_path)
    if not path.exists(): return None    # missing file degrades to None, never raises
    async with await anyio.open_file(path, 'rb') as f:
        screenshot_data = await f.read()
    return base64.b64encode(screenshot_data).decode('utf-8')
```
**Flow:** session captures a base64 screenshot → `store_screenshot` decodes and writes `step_{n}.png` through async file IO → the returned path is what history items keep → GIF renderer / judge / eval paths call `get_screenshot(path)` to re-materialize bytes only when needed → both calls are wrapped in `observe_debug(ignore_input=True, ignore_output=True)` so even in Laminar debug mode the span carries neither the base64 argument nor the returned image.
**Invariant:** image bytes cross this boundary exactly once per direction and never persist in Python objects: write-side returns a path (bytes become garbage immediately), read-side is fail-soft (`None` for empty path AND missing file). Telemetry hygiene is enforced by decorator args (`ignore_input/ignore_output`) that flow into lmnr's span factory; outside debug mode the decorator is a verified no-op (`observability.py:134-183`). The service itself never raises on bad input.
**Probe:** wiring test executed context: `tests/ci/test_beta_agent.py::test_beta_agent_exposes_setup_helper_methods` asserts `agent.screenshot_service` is a `ScreenshotService` bound to `agent.agent_directory`. Executed round-trip probe (repo .venv): `store_screenshot(b64, 3)` → `step_3.png` under `<dir>/screenshots/` with byte-identical disk content; `get_screenshot` round-trip equals original b64; missing path and empty path both → `None`. No dedicated unit test covers the service methods themselves — documented caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "ScreenshotService store_screenshot get_screenshot agent_directory screenshots dir", limit: 8, fields: ["lines"] });
```
Top hits: all three methods + class at exactly :13-52; nearest neighbor `BrowserStateHistory.get_screenshot` (:125-142) is the history-view accessor over stored paths.

## Verdict
Adopt the path-ledger pattern: persist binary artifacts to a per-run directory keyed by step number, keep only paths in history, and lazily re-encode for consumers that need pixels. Adapt the naming scheme and storage root to your product. Keep the `observe_debug(ignore_input=True, ignore_output=True)` wrapper on ANY function whose arguments or returns are images — that pairing is what makes the telemetry plane safe. Omit nothing else; the module is minimal by design.
