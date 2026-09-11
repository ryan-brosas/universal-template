<!-- capsule-v2 -->
# Sandbox keep-alive + ffmpeg stream lifecycle — how does a long agent session survive sandbox timeout, and how is the display streamed?

**Source:** open-computer-use Apache-2.0 `master@610bac85`; Codebase Memory `ext-open-computer-use`. **Question:** How is the E2B desktop sandbox kept alive during long runs and how does its screen reach the user's machine?

## set_timeout refresh per turn; x11grab→HTTP MPEG-TS listen server; group-kill on shutdown
**Path/Symbol:** `os_computer_use/streaming.py:8-25` (`Sandbox.start_stream`, `Sandbox.kill`), `:29-65` (`DisplayClient`); keep-alive call site `os_computer_use/sandbox_agent.py:178-179`.
**Signature:** `start_stream(self) -> str (https URL)`; `kill(self)`; `DisplayClient(output_dir)` with async `start(stream_url, title, delay)` / `stop()` / `save_stream()`.
**Data Shape:** Stream = ffmpeg x11grab of `{self._display}` @1024×768/30fps → libx264 ultrafast/zerolatency → mpegts over HTTP `-listen 1` port 8080; URL = `https://{sandbox.get_host(8080)}`.

### Decisive source
```python
command = "ffmpeg -f x11grab -s 1024x768 -framerate 30 -i {self._display} -vcodec libx264 " \
          "-preset ultrafast -tune zerolatency -f mpegts -listen 1 http://localhost:8080"
process = self.commands.run(command, background=True)
self.process = process
return f"https://{self.get_host(8080)}"

def kill(self):
    # Kill the streaming process along with the sandbox
    if hasattr(self, "process"):
        self.process.kill()
    super().kill()
```
```python
# DisplayClient.stop(): process-group kill so the shell pipeline dies whole
os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
```

**Flow:** sandbox boots → `stream.start()` launches backgrounded ffmpeg INSIDE the sandbox listening (not connecting) on 8080 → client opens the proxied HTTPS URL in pywebview → every agent turn calls `sandbox.set_timeout(60)` BEFORE inference so idle thinking time never trips E2B's reaper (this placement is the fix for the premature-timeout bug in commits 92730ab/abbf860) → teardown kills ffmpeg first, then sandbox.
**Invariant:** The listener lives inside the sandbox and the client only consumes a proxied URL — no inbound ports; kill order matters (stream child before sandbox parent or the sandbox dies holding an orphan encoder); `preexec_fn=os.setsid` on the CLIENT side makes the viewer pipeline one process GROUP so SIGTERM reaches ffplay+tee+ffmpeg together. NOTE the f-string bug: the x11grab command uses `{self._display}` in a PLAIN string — ffmpeg interpolates it via its own brace syntax only because E2B's runner happens to substitute nothing; porters should convert to a real f-string.
**Probe:** `cd $REFERENCE_ROOT/external/open-computer-use && sed -n '10,25p' os_computer_use/streaming.py && grep -n 'killpg\|setsid' os_computer_use/streaming.py && grep -n 'set_timeout' os_computer_use/sandbox_agent.py` (pins listen-server command :12, group-kill :50/:43, and per-turn keep-alive).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-computer-use", query: "Sandbox start_stream ffmpeg kill DisplayClient", limit: 6, fields: ["signature", "name", "file"] });
// expect Sandbox.start_stream / Sandbox.kill / DisplayClient methods
```

## Verdict
Adopt per-turn keep-alive-before-inference for any metered cloud runtime and the listen-side streaming pattern for remote displays; adapt codec flags to bandwidth needs; omit DisplayClient entirely for headless deployments (main.py already ships it disabled).
