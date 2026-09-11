<!-- capsule-v2 -->
# pycharm matplotlib display shim — how does an IDE receive plots from a headless `plt.show()`?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** How do you replace a GUI matplotlib backend so plots travel to an IDE over an importable, dependency-free channel?

## Agg backend + mime-bundle data object + plain-HTTP IDE endpoint

**Path/Symbol:** `plugins/python-ce/helpers/pycharm_matplotlib_backend/backend_interagg.py`:34-46 `Show`; :81-121 `FigureCanvasInterAgg.show`; :132-143 `FigureManagerInterAgg`; :146-165 `DisplayDataObject._repr_display_`; :168-169 export tail. Transport: `plugins/python-ce/helpers/pycharm_display/datalore/display/display_.py`:21-28 env config; :31-54 `display`; :73-92 `_send_display_message` + :57-70 `try_empty_proxy`.
**Signature:** `_repr_display_(self) -> ('pycharm-matplotlib', body)`; `display(data)` duck-types on callable `_repr_display_`; body = `{plot_index, image_width, image_base64, html_string, session_id}`.
**Data Shape:** PNG bytes → base64 str in the message body; the whole bundle is JSON-POSTed to `http://127.0.0.1:<PORT>/api/python.scientific?project=<PYCHARM_PROJECT_ID>&token=<PYCHARM_UUID>`.

### Decisive source
```python
class FigureManagerInterAgg(FigureManagerBase):
    def __init__(self, canvas, num):
        ...
        global index; index += 1          # per-figure counter (seeded by PYCHARM_MATPLOTLIB_INDEX)
    def show(self, **kwargs):
        self.canvas.show()
        Gcf.destroy(self._num)            # ONE-SHOT: figure is destroyed right after display

# FigureCanvasInterAgg.show():
if len(set(buffer)) <= 1:                 # empty/blank render guard
    return
for elem in self.figure.axes:
    if isinstance(elem, Axes3D):
        html_string = STRING_3D           # '3D' marker INSTEAD of mpld3 html (mpld3 can't do 3D)
plot_index = index if os.getenv("PYCHARM_MATPLOTLIB_INTERACTIVE", False) else -1
display(DisplayDataObject(plot_index, width, buffer, html_string))

def _repr_display_(self):                 # session_id = PYCHARM_PLOTS_CONSOLE_ID or pid
    return ('pycharm-matplotlib', body)

# transport (datalore/display/display_.py) — NOT a socket: HTTP POST
url = HOST + ":" + str(PORT) + "/api/python.scientific?project=" + PROJECT_HASH + "&token=" + PYCHARM_UUID
urllib_request.urlopen(url, buffer)       # on failure: retry via ProxyHandler({}) — auto-detected
                                          # proxies break localhost delivery
```
Backend export contract (module tail): `FigureCanvas = FigureCanvasAgg; FigureManager = FigureManagerInterAgg`; `Show.mainloop()` is a no-op so the pyplot event loop never blocks.

**Flow:** IDE sets `PYCHARM_DISPLAY_PORT` (+ project id/token, optional `PYCHARM_PLOTS_CONSOLE_ID`, `PYCHARM_INTERACTIVE_PLOTS` for mpld3) and points matplotlib at this module backend → user code calls `plt.show()` → `Show.__call__` iterates ALL `Gcf` managers → each manager.show() renders PNG via Agg into BytesIO, guards blank output, marks 3D or builds mpld3 HTML, wraps bytes+width+index+session in DisplayDataObject → `display()` duck-calls `_repr_display_()`, validates the 2-tuple, standardizes values, JSON-POSTs `{type, body}` to the IDE's localhost scientific endpoint → manager destroys its figure.
**Invariant:** Delivery degrades gracefully, never crashes user code: no PORT (`PYCHARM_DISPLAY_PORT=-1`→None) or blank render falls back to silent skip / `print(repr(data))`. Proxy handling must end in an EMPTY-proxy retry because urllib's auto-detected proxy settings break connections to 127.0.0.1. Figures are one-shot: shown ⇒ destroyed, so a second `plt.show()` cannot re-emit them.
**Probe:** executed 2026-08-26 — 12-check AST/text battery PASS 12/12 against shipped source: one-shot destroy ordering, `len(set(buffer))<=1`, `'3D'` marker, interactive gate + `plot_index = index if ... else -1`, counter seed, session-id ladder, `('pycharm-matplotlib', body)` tuple, export-tail assignments, `-1`→None port disable, `/api/python.scientific?project=`+`&token=`, proxy ladder (`ProxyHandler({})` + `PYCHARM_DISPLAY_HTTP_PROXY`), duck-typed `getattr(data,'_repr_display_',None)`.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pycharm_matplotlib_backend.backend_interagg.FigureCanvasInterAgg.show" });
// -> start_line 81 end_line 121 — EXECUTED (byte-matches direct read); also display_.display :31-54 and DisplayDataObject._repr_display_ :154-165 — EXECUTED
```

## Verdict
Adopt: headless-Agg canvas + a small data object whose `_repr_display_` returns `(mime-type, dict)` + a fire-and-forget localhost HTTP transport with explicit-port enablement and graceful print fallback. The empty-proxy retry ladder is mandatory for any urllib-based localhost channel. Adapt the endpoint path/auth token to your front-end. Omit the mpld3 interactive-HTML branch unless you also want zoomable plots, and the PY2 urllib2 import split.
