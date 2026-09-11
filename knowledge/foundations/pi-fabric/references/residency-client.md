<!-- capsule-v2 -->
# Residency client — how does a UI process drive a detached resident host (spawn, command/response, delivery drain) over pure file I/O?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the client-side half of the outliving-the-UI protocol — how are requests issued and responses matched without sockets?

## Request/response by atomic JSON files, liveness-checked at every wait
**Path/Symbol:** `src/residency/client.ts:ResidencyClient` (:56-404), `ensureHost` (:99-121), `#command` (:285-302), `#liveOwner` (:355-366), `#metadata` (:325-353), `#deliver` (:379-403).
**Signature:** `ensureHost(): Promise<ResidentHostOwner>`, `#command(cmd: ResidentCommand, signal?): Promise<ResidentCommandResponse>`, `waitAgent(id)`, `cleanupAgent(id, deleteBranch?)`.
**Data Shape:** residency root holds `config.json`, `owner.json {format, hostId, pid}`, `error.json`, `requests/<uuid>.json`, `responses/<uuid>.json`, `agents/<id>.json`, `runs/<id>/`; constants: startup 10s, command 30s, poll 100ms; agent ids must match `^[a-f0-9]{32}$`.

### Decisive source
```ts
async #command(command, signal) {
  const responsePath = path.join(this.#responsesPath, `${command.requestId}.json`);
  atomicWrite(path.join(this.#requestsPath, `${command.requestId}.json`), command);
  const deadline = Date.now() + COMMAND_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (signal?.aborted) throw new Error("Fabric residency request was aborted");
    const response = readJson<ResidentCommandResponse>(responsePath);
    if (response?.format === RESIDENT_HOST_FORMAT && response.requestId === command.requestId) {
      fs.rmSync(responsePath, { force: true });       // consume the response exactly once
      if (!response.ok) throw new Error(response.error ?? "…rejected request");
      return response;
    }
    const owner = this.#liveOwner();                  // host died mid-request?
    if (!owner) throw new Error("Fabric resident host exited while processing a request");
    await delay(STATUS_POLL_MS);
  }
  throw new Error(`Timed out waiting for Fabric residency request ${command.requestId}`);
}
#liveOwner() {
  const owner = readJson(this.#ownerPath);
  return owner?.format === RESIDENT_HOST_FORMAT && owner.hostId === this.hostId
    && Number.isSafeInteger(owner.pid) && processIsAlive(owner.pid) ? owner : undefined;
}
```

**Flow:** ensureHost writes config atomically, returns the live owner if `owner.json` names a living pid, else clears `error.json`, spawns the host detached, polls owner/error until live or failed (startup timeout) → commands pair an atomic request write with a polled response file consumed on read → durable agent metadata is validated against path/branch conventions before any action (`runs/<id>` exact resolve, worktree under `<tmp>/pi-fabric-worktrees/<id>`, branch `pi-fabric/*-<id8>`) → cleanup falls back to direct file/git operations when no host is alive → cross-host deliveries drain from mesh keys (`updatedBy.id === this.hostId`) and are deleted via mesh CAS after handoff.
**Invariant:** every blocking loop checks BOTH the wall clock AND host liveness — a dead host surfaces as a thrown indeterminate-outcome error instead of a silent hang; responses are single-consumer (deleted after read); metadata that doesn't resolve to the expected paths is treated as unknown rather than acted upon.
**Probe:** `tests/residency.test.ts:179` ("keeps a durable actor responsive after its originating Main closes"), `:323` ("queues passive actor delivery until Main resumes"), `:410` ("completes and cleans a durable agent after its originating Main closes").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ResidencyClient ensureHost command response requests responses liveOwner processIsAlive deliver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the file-based request/response protocol with per-wait liveness checks and single-consume responses plus paranoid metadata validation; adapt directory layout/timeouts to your host; omit git worktree cleanup specifics. Pairs with the existing resident-host-protocol capsule (host side).
