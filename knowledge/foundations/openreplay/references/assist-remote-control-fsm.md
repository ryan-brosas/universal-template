<!-- capsule-v2 -->
# Assist remote-control consent FSM — what state machine gates agent mouse/keyboard injection?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** How is control granted/requested/released so an injected click can never outlive its grant?

## Requesting→Enabled→Disabled with sessionStorage persistence
**Path/Symbol:** `tracker/tracker-assist/src/RemoteControl.ts` — `RCStatus`, `requestControl` (:43–75), `releaseControl` (:77–92), `grantControl` (:94–107), `reconnect` (:32–40), input guards (`click/move/input`: :114–149).
**Signature:** `requestControl(id)`; `grantControl(id, skipUpdate?)`; `releaseControl(isDenied?, keepId?, skipUpdate?)`.
**Data Shape:** status enum; `agentID: string | null`; persistence key `session_control_peer_key` in sessionStorage; 30 s request timeout.

### Decisive source
```ts
requestControl = (id) => {
    if (this.status === RCStatus.Enabled) return this.onBusy(id)
    if (this.agentID !== null) { this.releaseControl(); return }
    setTimeout(() => { if (this.status === RCStatus.Requesting) this.releaseControl() }, 30000)
    ...
}
input = (id, value) => {
    if (id !== this.agentID || !this.mouse || !this.focused) { return }   // guard every action
```

**Flow:** agent requests → user ConfirmWindow → allow ⇒ grantControl stores peer id in sessionStorage and mounts the synthetic Mouse overlay → deny/timeout ⇒ release(true). Page reload calls `reconnect(ids)` which re-grants ONLY if the stored id is still connected. Every mouse event handler first checks `id === this.agentID`.
**Invariant:** Actions are dropped unless the event's agent id matches the CURRENT grant — a stale or racing agent must not move/click. Release clears storage + overlay atomically. Requesting state self-expires after 30 s.
**Probe:** `grep -c 'session_control_peer_key' tracker/tracker-assist/src/RemoteControl.ts` → `4`; `grep -c 'id !== this.agentID' tracker/tracker-assist/src/RemoteControl.ts` → `2`; `grep -c '30000' tracker/tracker-assist/src/RemoteControl.ts` → `1`. Direct tests: none upstream (grep-pinned).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "RemoteControl grantControl releaseControl requestControl", limit: 10 });
```

## Verdict
Adopt per-event id guard + reload re-grant. Adapt UI confirmation to your stack. Omit drag-camera hooks if unused.
