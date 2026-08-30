<!-- capsule-v2 -->
# Browser-driven review harness — how does a CLI drive a real browser to render and sample a video composition?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Reviewing generated video needs a real renderer — how does the CLI serve the composition, drive the browser, and collect a machine-readable verdict?

## local HTTP serve + harness subprocess + marker-line result protocol
**Path/Symbol:** `src/browser_harness/video_render.py:serve` (:87-100), `run_harness` (:106-124), `_review_browser` (:126-...), `review_samples` (:57-79), `review` (:277-...), `export` (:413-...).
**Signature:** `serve(recording)` (contextmanager yielding `http://127.0.0.1:<port>/video.html`); `run_harness(code, timeout=60) -> dict`; `review(recording) -> int`.
**Data Shape:** `MARKER = "__BH_VIDEO_RESULT__="`; review artifacts dir `.renderer-review/`; `_QuietHandler` suppresses HTTP logs.

### Decisive source
```python
def run_harness(code, timeout=60):
    env = {**os.environ, "BH_RECORD": "0"}               # never record the review
    proc = subprocess.run(_harness_command(), input=code, text=True,
        capture_output=True, env=env, timeout=timeout, check=False)
    if proc.returncode: raise RuntimeError(f"browser review failed: {proc.stderr or proc.stdout}")
    for line in reversed(proc.stdout.splitlines()):      # LAST marker line wins
        if line.startswith(MARKER):
            return json.loads(line[len(MARKER):])
    raise RuntimeError(f"browser review returned no result: {proc.stdout[-1000:]}")

def review_samples(comp):
    # one stable state per beat, plus every explanation reveal
    for index, beat in enumerate(comp.get("beats") or [], 1):
        if beat.get("kind") == "explanation" and beat.get("points"):
            ...samples.append({"time": ..., "label": f"beat {index} · {point['label']}"})
        else:
            samples.append({"time": ..., "label": f"beat {index}"})
```

**Flow:** `serve` starts a ThreadingHTTPServer on an ephemeral port serving the recording dir → `_review_browser` builds a Python payload (url + samples + reviewDir + marker) → `run_harness` pipes it as code into `browser_harness.run` → the browser navigates, seeks each sample time, captures to `.renderer-review/`, and prints a `__BH_VIDEO_RESULT__=` JSON line → the CLI parses the LAST such line.
**Invariant:** review runs with `BH_RECORD=0` (never self-records); the result protocol is a sentinel-prefixed JSON line on stdout (last occurrence wins); the HTTP server is ephemeral + daemon-threaded and torn down in `finally`; the review browser is the harness itself (dogfooding).
**Probe:** no direct unit test (needs a live browser) — coverage caveat: `review_samples` is pure and deterministic; the marker protocol is verified by reading `run_harness`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "video_render run_harness marker review_samples serve", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the serve + subprocess-drive + sentinel-line-result pattern for any browser-rendered review/export pipeline; adapt the marker and sample strategy; omit nothing. Coverage caveat: live-browser path untested upstream.
