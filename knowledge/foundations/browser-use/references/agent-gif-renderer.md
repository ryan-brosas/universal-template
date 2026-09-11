<!-- capsule-v2 -->
# History-GIF renderer — placeholder-screenshot filtering, CJK font ladder, and unicode-escape overlay text

**Source:** browser-use MIT `main@3c989dc0`; Codebase Memory `browser-use`. **Question:** How do you render an agent-history GIF that survives about:blank placeholders, non-Latin goal text, and machines with no fonts installed?

## create_history_gif: filter → font ladder → task frame → overlays → fd cleanup
**Path/Symbol:** `browser_use/agent/gif.py:create_history_gif` (35-215), `decode_unicode_escapes_to_utf8` (20-32), `_create_task_frame` (218-294, dynamic font sizing), `_add_overlay_to_image` (297-394), `_wrap_text` (397-429).
**Signature:** `def create_history_gif(task: str, history: AgentHistoryList, output_path='agent_history.gif', duration=3000, show_goals=True, ...) -> None`
**Data Shape:** screenshots = base64 PNGs incl. None and the 4px about:blank placeholder (`PLACEHOLDER_4PX_SCREENSHOT`); output = GIF (loop=0, optimize=False); all PIL images closed in finally.

### Decisive source
```python
def decode_unicode_escapes_to_utf8(text):
    if r'\u' not in text: return text          # fast path, no escapes present
    try:
        return text.encode('latin1').decode('unicode_escape')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text                             # never raise on bad goal text
...
font_options = ['PingFang','STHeiti Medium','Microsoft YaHei','SimHei','SimSun',
    'Noto Sans CJK SC','WenQuanYi Micro Hei','Helvetica','Arial','DejaVuSans','Verdana']
... except OSError: regular_font = ImageFont.load_default()   # ultimate fallback
...
finally:
    for img in images: img.close()              # release file descriptors
```

**Flow:** skip when no history/screenshots → find FIRST real screenshot (≠4px placeholder; new-tab pages skipped per-item via `is_new_tab_page`) → CJK-first font ladder with Windows absolute-path join (`CONFIG.WIN_FONT_DIR`) falling back to PIL default → optional task frame (black canvas sized from first screenshot, dynamic font shrink for tasks >200 chars via logarithmic decay, min floor) → per step: decode b64 → overlay step number (rounded rect, bottom-left) + wrapped goal text above it → save all frames → finally close every image.
**Invariant:** placeholder/new-tab frames MUST be dropped or the GIF opens with blank white frames; goal text goes through `decode_unicode_escapes_to_utf8` TWICE (once at overlay entry, once inside `_wrap_text`) because model outputs carry literal `\uXXXX` sequences from JSON round-trips — without latin1→unicode_escape re-decoding Chinese/Arabic goals render as mojibake. The function NEVER raises on undecodable text. FD hygiene: every opened PIL image closed even on save failure.
**Probe:** deterministic source pins: `grep -n "PLACEHOLDER_4PX_SCREENSHOT\|latin1\|load_default" browser_use/agent/gif.py` (:77/:142/:166/:29/:120). Coverage caveat: no upstream unit file (PIL rendering not asserted anywhere in tests/).
**Retrieve note:** graph anchor `create_history_gif Function 35-215` resolves agent/gif.py line-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "create_history_gif _wrap_text decode_unicode_escapes_to_utf8", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt placeholder-filtering + escape-decoding + font-ladder-with-default for any media render of model text; adapt frame layout/typography freely; omit logo compositing unless you ship the static asset.
