<!-- capsule-v2 -->
# Off-screen window scrape mode — how do I keep a browser fully rendered but out of the operator's way without going headless?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`fill_data` :218–220; restore `applications_loop` :251–252); Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** how do you hide automation's browser from the human using the machine while keeping the full non-headless rendering pipeline?

## Shrink to 1×1, park at (2000,2000); maximize when working
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.fill_data` (:218–220), called from `start_apply` (:224); inverse `browser.set_window_position(1, 1)` + `maximize_window()` at `applications_loop` entry (:251–252).
**Signature:** `fill_data() -> None` — two WebDriver window calls, no arguments.
**Data Shape:** geometry only — `set_window_size(1, 1)`, `set_window_position(2000, 2000)`; no flags, no headless switch, no display env assumptions.

### Decisive source
```python
def fill_data(self) -> None:
    self.browser.set_window_size(1, 1)
    self.browser.set_window_position(2000, 2000)     # off every visible monitor

# ...and when a real search session starts (:251-252):
self.browser.set_window_position(1, 1)
self.browser.maximize_window()
```

**Flow:** bot construction → fill_data parks the window at 1×1 far outside the desktop viewport → when a search session begins, applications_loop restores position AND maximizes so lazy-loading layouts get real viewport dimensions during scraping.
**Invariant:** the renderer keeps running exactly as in a headed session (no --headless flag to trip bot-detection heuristics or break screenshot-dependent code paths), while the operator's desktop stays unobstructed; the restore step is load-bearing — LinkedIn's results list renders lazily against viewport size, so scraping happens MAXIMIZED even though setup ran hidden.
**Probe:** repo ships no test suite — coverage caveat recorded. Deterministic probes verified byte-for-byte at HEAD 8471c58: `grep -n "set_window_size\|set_window_position\|maximize_window" easyapplybot.py` ⇒ :219/:220 (park) and :251/:252 (restore/maximize) — exactly one park site, one restore site.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "fill_data window size position maximize", limit: 5 });
// ⇒ EasyApplyBot.fill_data :218-220 (resolved live this pass)
```

## Verdict
Adopt geometric hiding (shrink+park / restore+maximize pairing) for long unattended runs on operator machines where headless changes behavior or detection surface; adapt park coordinates to the host's actual monitor topology (a 4K multi-monitor layout can expose x=2000); omit nothing structural. Contrast: puppeteer-flag-stack shapes LAUNCH capabilities; this seam shapes WINDOW GEOMETRY at run time. Caveat: source-read only.
