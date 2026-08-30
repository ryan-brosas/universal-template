<!-- capsule-v2 -->
# Herdr newline-JSON socket client — how do you drive a paned-terminal host over a Unix socket/named pipe with request timeouts, response caps, and optional attach metadata?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the wire contract for launching a worker inside a Herdr workspace pane, and how does the client stay safe against hung servers and oversized responses?

## One-shot request/response with 3s timeout, 1MB cap, and settle-once latching
**Path/Symbol:** `src/agents/transports/herdr-transport.ts` whole file (170L): constants (:11-12), response types (:14-33), `endpointFor` (:35-36), `responseError` (:38-42), class (:44-119), `#request` (:121-169). Direct tests `tests/herdr-transport.test.ts` whole (137L).
**Signature:** `new HerdrTransport(environment: NodeJS.ProcessEnv = process.env)`; `available(): Promise<boolean>`; `launch(request): Promise<AgentTransportHandle>`; `#request({method, params}): Promise<unknown>`.
**Data Shape:** env gate `HERDR_ENV === "1"` + `HERDR_SOCKET_PATH` + `HERDR_WORKSPACE_ID`; requests `{id: "pi-fabric:<uuid>", method, params}` + `\n`; responses `{id, result:{type, layout:{root:{pane_id}}, pane:{terminal_id}}} | {error:{code, message}}`.

### Decisive source
```ts
const REQUEST_TIMEOUT_MS = 3_000;
const MAX_RESPONSE_BYTES = 1 * 1024 * 1024;
// win32 named pipe vs unix socket path
const endpointFor = (socketPath) =>
  process.platform === "win32" ? `\\\\.\\pipe\\${socketPath}` : socketPath;
const finish = (error?, value?) => {
  if (settled) return;              // ONE settlement per request — later events ignored
  settled = true;
  clearTimeout(timeout);
  socket.destroy();
  if (error) reject(error); else resolve(value);
};
socket.on("data", (chunk) => {
  const newline = chunk.indexOf("\n");            // FIRST newline terminates the frame
  const captured = newline < 0 ? chunk : chunk.slice(0, newline);
  responseBytes += Buffer.byteLength(captured, "utf8");
  if (responseBytes > MAX_RESPONSE_BYTES) return finish(new Error(`…exceeds ${MAX_RESPONSE_BYTES} bytes`));
  // … parse at first newline; JSON failure also settles the promise as error
});
socket.on("end", () => finish(new Error("Herdr API closed without a response")));
```

**Flow:** availability = env triple present AND a live `ping` round-trip (availability may be a live check). Launch sends `layout.apply {workspace_id, tab_label: name, focus:false, root:{type:"pane", label:name, cwd, command: scriptSpawnArgs(...)}}` — the worker command is an ARGV ARRAY (server joins/quoting is the host's job), verified byte-exact by the test's `expect(apply?.params).toEqual(...)` with spaces in cwd/task-file. A missing/`type !== "layout_apply"` response or absent `pane_id` throws `Herdr layout.apply did not return a pane id`. The follow-up `pane.get` fetching `terminal_id` for `attachCommand: "herdr terminal attach <id>"` is OPTIONAL — its failure is swallowed because very short runs exit before attach metadata exists (:94-96). Handle verbs: `isAlive` = `pane.get` success, `stop` = best-effort `pane.close`.
**Invariant:** every request settles EXACTLY once (timeout/error/data/end all funnel through the settled latch); the frame is strictly one line of JSON — bytes past the first newline never count toward the cap nor get parsed; timeout is `.unref()`ed so a pending request cannot hold the event loop open; errors from responses carry the server's `code:` prefix when present.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -n "let settled = false" src/agents/transports/herdr-transport.ts | wc -l'` → 1 (:129); `grep -c "if (settled) return;" src/agents/transports/herdr-transport.ts` → 1 (:131); `grep -n "MAX_RESPONSE_BYTES = " src/agents/transports/herdr-transport.ts | wc -l` → 1 (:12); `grep -n "REQUEST_TIMEOUT_MS = " src/agents/transports/herdr-transport.ts | wc -l` → 1 (:11); tests pin the full handshake against an in-process fake server (`tests/herdr-transport.test.ts:111-115` pins sessionId `w1:p2` + attachCommand `herdr terminal attach term_worker`; :117-132 pins the argv-array command with spaced paths; :133-135 pins alive→stop→dead).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "herdr transport layout.apply pane socket", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #3 resolves `HerdrTransport.launch` :65-119 line-exact.)

## Verdict
Adopt the single-settlement socket client (timeout + cap + latch), argv-array command payloads, and optional-metadata tolerance for any JSON-line IPC you control on both ends; adapt method names/layout grammar to your terminal host; omit the win32 pipe branch if unix-only. Fully direct-test-pinned via an in-process fake server — no coverage caveat.
