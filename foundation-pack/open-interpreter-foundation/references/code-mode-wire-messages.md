<!-- capsule-v2 -->
# code-mode-wire-messages — what does the host↔client protocol actually put on the wire?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** Which message types, tag names, and lane rules define the host protocol?

## ClientToHost / HostToClient / HostRequest taxonomies
**Path/Symbol:** `codex-rs/code-mode-protocol/src/host/message.rs` (:1-320).
**Data Shape:** serde internally-tagged with `type` (messages) and `method` (requests), `rename_all = "camelCase"`, `deny_unknown_fields`; method names are slash-style (`session/open`, `session/execute`, `session/wait`, `session/terminate`, `session/close`).

### Decisive source
```rust
#[derive(Debug, Deserialize, PartialEq, Serialize)]
#[serde(deny_unknown_fields, tag = "type", rename_all_fields = "camelCase")]
pub enum HostToClient {
    #[serde(rename = "connection/ready")]      HostHello(HostHello),
    #[serde(rename = "connection/rejected")]   HandshakeRejected { reason: HandshakeRejectReason },
    #[serde(rename = "operation/response")]    Response { id, result },
    ...
}
// lanes: CancelRequest|Request => Control; DelegateResponse => Bulk
```

**Flow:** hello negotiation → requests carry client-chosen RequestId (i64 transparent newtype) → host answers operation/response OR streams initial/cell events for execute; delegate traffic flows the REVERSE direction as DelegateRequest/CancelDelegateRequest answered by DelegateResponse. Wire* structs mirror domain types so protocol evolution never leaks Rust enums directly.
**Flow (cell streaming):** per-cell InitialResponse + cell event messages keep the execute request non-blocking; CellClosed marks terminal.
**Invariant:** deny_unknown_fields makes the parser strict — forward-compat happens via capabilities/versioning, not ignored fields. NonEmptyString-backed ids reject empty/whitespace at DESERIALIZATION time, so malformed peers fail at the boundary.
**Probe:** `host_tests.rs` + `codec_tests.rs` round-trip the full taxonomy at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "ClientToHost HostToClient HostRequest transport_lane", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt tagged-camelCase strict wire schema, slash-method request naming, and id newtypes validated at parse. Omit exact field lists when adapting.
