<!-- capsule-v2 -->
# WaitingSpinner — 0.5s visibility delay, class-shared frame position, and truncation-safe backspace math

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How do you show an LLM-call spinner that never flickers on fast responses, survives non-TTY pipes, and never corrupts the line when the text is longer than the terminal?

## Pre-rendered bounce animation + delayed first paint + padding-then-backspaces cursor repair
**Path/Symbol:** `aider/waiting.py`: `Spinner` (:23, `last_frame_idx` CLASS variable shared across instances), `step(text=None)` (:105), `_supports_unicode()` (:83, probe-write `░█` + backspaces then blank them), `end()` (:162), `WaitingSpinner` thread wrapper (:171, daemon thread + `threading.Event`, context-manager via `__enter__/__exit__`).
**Signature:** `step` gates: skip entirely if not TTY; first paint only after `now - start_time >= 0.5`; repaint throttle `< 0.1s`; frame advance `(idx+1) % len(frames)` persisted back to the CLASS variable so successive spinners continue the bounce seamlessly.
**Data Shape:** 19 ASCII frames `"=#"`→scan; unicode palette swap via `str.maketrans("=#", "░█")`; width-2 margin subtracted from console width.

### Decisive source
```python
num_backspaces = total_chars_written_on_line - scan_char_abs_pos
# non-positive when the scan char was truncated off the visible line:
# write (effectively) 0 backspaces; cursor stays at end of line
sys.stdout.write("\b" * num_backspaces)
...
def stop(self):
    self._stop_event.set()
    if self._thread.is_alive():
        self._thread.join(timeout=self.delay)
    self.spinner.end()
```

**Flow:** start() launches a daemon thread stepping every `delay=0.15s` → step renders `frame + " " + text`, pads with spaces to erase any longer previous line (`padding_to_clear = max(0, last_display_len - len)`) → positions the cursor at the scan char via computed backspaces → stop() sets the event, joins for one delay period, then end() clears the whole line length and restores the cursor.
**Invariant:** output is single-line idempotent — every repaint erases exactly what it wrote before (length-tracked); non-TTY stdout produces NOTHING (pipes/logs stay clean); the 0.5s delay means sub-half-second LLM calls never see a spinner at all.
**Probe:** NO upstream test file exists for waiting.py (source-pinned caveat). Deterministic: `grep -c 'backspaces' aider/waiting.py` → **5** (:147/:153/:156 comments + :158 assignment + :159 use — anchor precisely with `grep -nF 'num_backspaces = total_chars_written_on_line' aider/waiting.py` → exactly :158).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "WaitingSpinner", limit: 3 });
// rank-1: aider.aider.waiting.WaitingSpinner.__init__ aider/waiting.py 174-178
```

## Verdict
Adopt verbatim as the reference terminal-spinner contract (delay/throttle/pad/backspace quartet); adapt frames. The class-level frame index is deliberate continuity polish; the truncation-tolerant backspace clamp is the part porters get wrong and produce garbage lines on narrow terminals.
