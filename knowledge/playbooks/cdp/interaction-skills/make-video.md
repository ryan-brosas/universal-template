# Record a session with rrweb

Recording captures the live DOM with [rrweb](https://github.com/rrweb-io/rrweb),
not screenshots and not a cinematic edit. Start/stop are the primitives;
replay is the rrweb Replayer.

## Capture with consent

Fresh installs do not record. `startRecording()` is the opt-in for that task.
The session must already be connected.

```js
await session.connect()
const recordingDir = await startRecording('azure-admin', 'Make Aitor superadmin')
// Drive the browser (or let the user). Clicks, typing, and navigations in
// instrumented pages become rrweb events — including real user input.
await stopRecording()
return recordingDir
```

Each recording is a directory under `~/.browser-harness-js/recordings`:

- `meta.json` — name, title, start time, `engine: "rrweb"`
- `rrweb.jsonl` — one `{ sid, e }` line per rrweb event (`sid` is the CDP page session)

The first `startRecording()` / `recordings replay` downloads pinned rrweb 2.1.1
(`dist/rrweb.umd.min.cjs`) from jsDelivr into `~/.browser-harness-js/cache/` and
verifies `sha256`. Later calls reuse that file (offline).
`CDP_RRWEB_JS=/path/to/rrweb.umd.min.cjs` overrides the download.

Input values are masked (`maskAllInputs`). Canvas and font collection are off.
Large snapshots are chunked through `Runtime.addBinding` so they never travel
as one CDP WebSocket payload. Cross-origin iframes are **not** instrumented
(same limitation as [record-cross-tab.md](record-cross-tab.md)).

`CDP_RECORD=0` disables start. `recordings enable` / `disable` only persist a
local preference; they do not start capture by themselves.

```bash
browser-harness-js recordings
browser-harness-js recordings enable
browser-harness-js recordings disable
browser-harness-js recordings --latest
```

A daemon `--restart` drops in-page recorders. The on-disk marker from a previous
process is treated as stale the next time `startRecording()` runs.

## Replay

```bash
browser-harness-js recordings replay <recording>
# or, after verifying timestamps match the task:
browser-harness-js recordings replay
```

Serves the recording on `127.0.0.1` and prints the URL. Pick a tab (`sid`) in
the bar, then Play / Pause. Ctrl+C stops the server. This is a fidelity replay
of captured DOM mutations, not an evidence-edited MP4.

## Traps

- **Connect first.** `startRecording()` injects into live page targets; it throws
  if the CDP session is not connected.
- **The DOM is the tape.** `Runtime.evaluate('element.click()')` still shows up
  if it mutates the page. There is no semantic `click_at_xy` / `goto_url` layer.
- **PII lives in the DOM.** Masked inputs are not a privacy review. Treat the
  jsonl as sensitive and keep it local.
- **Do not reenact** a finished task to manufacture a cleaner recording.
- **OOPIFs are separate targets.** See [record-cross-tab.md](record-cross-tab.md).
