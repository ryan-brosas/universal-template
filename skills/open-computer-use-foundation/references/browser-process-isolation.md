<!-- capsule-v2 -->
# Browser process-isolation viewer — why does a VNC window need a separate OS process?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How is the pywebview viewer kept from freezing the agent's asyncio loop, and how is it closed cleanly?

## multiprocessing.Process + command Queue + daemon poller thread
**Path/Symbol:** `os_computer_use/browser.py:7-14` (state), `:16-40` (`open`), `:42-52` (`close`), `:54-77` (`_create_window` staticmethod).
**Signature:** `open(url, width=None, height=None)`; `close()`; `_create_window(url, width, height, command_queue)` (static — must be picklable for Process spawn).
**Data Shape:** Command channel = `multiprocessing.Queue` carrying the single sentinel `"close"`; window height padded by a hardcoded `window_frame_height = 29` px so the 1024×768 VIEWPORT matches the sandbox display exactly.

### Decisive source
```python
self.webview_process = Process(
    target=self._create_window,
    args=(url, self.width, self.height, self.command_queue),
)
self.webview_process.start()
```
```python
# child side: GUI loop + 1s-close-poller thread
window = webview.create_window("Browser Window", url,
                               width=width, height=height + window_frame_height)
t = threading.Thread(target=check_queue); t.daemon = True; t.start()
webview.start()
```

**Flow:** open() spawns the webview event loop as its own PROCESS (GUI toolkits own their main loop and would otherwise block or fight asyncio) → parent stays interactive for the USER prompt → close() enqueues "close" → child's daemon thread polls at 1 Hz and calls `window.destroy()` → `join()` reaps.
**Invariant:** The viewer is deliberately fire-and-forget: no IPC back, no error propagation (a crashed child leaves `is_running` True — acceptable because main.py closes it in `finally`); the 29px frame compensation is the coupling that keeps agent click coordinates aligned with what the human watches. Polling (not blocking queue.get) is required because pywebview owns the child's main thread.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && grep -n 'Process(\|Queue()\|window_frame_height' os_computer_use/browser.py` (pins spawn :35, queue :12, and BOTH frame-height copies :11/:67 which MUST stay in sync).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "Browser webview create_window command_queue destroy", limit: 6, fields: ["signature", "name", "file"] });
// expect Browser.open/close/_create_window nodes
```

## Verdict
Adopt process-isolated viewers whenever a GUI toolkit must coexist with an async agent core; adapt the frame constant per platform WM; omit entirely in headless deployments (main.py treats the viewer as optional).
