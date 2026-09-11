<!-- capsule-v2 -->
# Streaming markdown window — stable-lines-to-scrollback vs live-repainted tail with render-time adaptive throttle

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you stream LLM markdown into a terminal so finished content lands in scrollback while the volatile tail keeps repainting?

## Stable/live split at live_window=6
**Path/Symbol:** `aider/mdstream.py`: `MarkdownStream.update(text, final=False)` (:149), `_render_markdown_to_lines(text)` (:122), class constants `min_delay = 1.0/20`, `live_window = 6` (:102-103), `NoInsetMarkdown` (:81).
**Signature:** `update(text: str, final: bool = False) -> None`; internal `self.printed` holds every line already emitted above the Live region.
**Data Shape:** full re-render each tick → `num_lines = len(lines) - live_window` (ALL lines when final); `show = lines[num_printed:num_lines]` goes to the console ABOVE the Live area (permanent scrollback); `lines[num_lines:]` repaints INSIDE the Live window.

### Decisive source
```python
now = time.time()
if not final and now - self.when < self.min_delay:
    return                                  # throttle: skip mid-interval updates
...
start = time.time()
lines = self._render_markdown_to_lines(text)
render_time = time.time() - start
self.min_delay = min(max(render_time * 10, 1.0 / 20), 2)   # adapt: floor 20fps, cap 2s
```
Live display is created lazily on FIRST update (`if not getattr(self, "_live_started", False)`), and the destructor plus `final=True` path both stop it; final also blanks the Live widget before stopping so no tail text freezes on screen.

**Flow:** chunk arrives → throttled? skip → render whole markdown to ANSI lines → newly-stable slice printed above → remainder becomes the Live payload → on final, everything is stable, Live cleared+stopped.
**Invariant:** stable lines are EMITTED EXACTLY ONCE (printed-prefix accounting via `len(self.printed)`); markdown renders better in scrollback than in a Live region — that asymmetry is why the split exists; update frequency self-tunes to ~10× render cost, clamped [50ms, 2s].
**Probe:** executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::mdstream-window-math` (render→stable/live partition is lossless; pad/unpad guards), repo venv GREEN. No upstream direct tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "MarkdownStream", limit: 5 });
// resolves: aider.aider.mdstream.MarkdownStream
```

## Verdict
Adopt the once-only stability ledger + adaptive throttle + lazy-Live lifecycle for any streaming TUI; adapt the rich-specific renderers (NoInset code blocks, left headings are cosmetic); omit the `__main__` demo harness. Coverage caveat: probe-pinned only.
