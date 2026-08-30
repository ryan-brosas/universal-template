<!-- capsule-v2 -->
# host-peer-bulk-lane — how do delegate callbacks share one connection with control traffic without head-of-line blocking?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How is delegate-call backpressure enforced and how do per-cell routes stream results?

## HostPeer pending + permit ledger
**Path/Symbol:** `codex-rs/code-mode-host/src/peer.rs` : `HostPeer` (:28-46), `PendingDelegate` (:48-52), `CellRoute` (:54-61); `code-mode-protocol/src/host/mod.rs` : `MAX_PENDING_DELEGATE_CALLS = 1_024`.
**Data Shape:** pending delegate calls keyed by DelegateRequestId, each holding an OWNED semaphore permit (backpressure = acquire blocks at 1024 in flight); cell routes keyed `(SessionId, CellId)` as Pending(VecDeque) → Active(mpsc 128) with a Notify on transitions.

### Decisive source
```rust
pub(super) struct HostPeer {
    outgoing_tx: mpsc::Sender<EncodedFrame>,
    bulk_tx: Option<mpsc::Sender<EncodedFrame>>,
    pending: Mutex<HashMap<DelegateRequestId, PendingDelegate>>,
    delegate_permits: Arc<Semaphore>,          // MAX_PENDING_DELEGATE_CALLS
    cell_routes: StdMutex<HashMap<(SessionId, CellId), CellRoute>>,
    ...
}
```

**Flow:** host wants the client to run a nested tool → acquire permit → send DelegateRequest on the BULK lane when dual-websocket negotiated (control lane otherwise) → client's DelegateResponse completes the oneshot → permit dropped. Responses that exceed the IPC frame limit are re-sent as structured errors (`respond` fallback) — a too-big answer becomes an error message, never a broken connection.
**Flow (lanes):** every message has a transport_lane; dual-lane connections REJECT wrong-lane messages (`allows_transport_lane` check in lib.rs read loop :215-217); biased select prioritizes CONTROL reads over bulk so session ops progress while callbacks flood.
**Invariant:** The permit is held until response arrival, not send — backpressure covers round-trips. Writer-task death fails the whole peer (`peer.fail`) rather than hanging pending calls.
**Probe:** `code-mode-host/src/grpc/robustness_tests.rs` + host_tests.rs at pin exercise writer failure and pairing timeouts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "HostPeer PendingDelegate MAX_PENDING_DELEGATE_CALLS TransportLane", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt permit-ledger backpressure, per-cell route buffers with Notify, lane discipline, and frame-overflow-to-error conversion. Adapt to your transport. Omit gRPC codec specifics.
