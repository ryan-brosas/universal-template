<!-- capsule-v2 -->
# Transport error taxonomy — how should wire failures surface as diagnostics, not panics?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** What is the minimal closed set of remote-call failure modes a workspace proxy must model?

## Four-variant enum with internalError/io diagnostic identity
**Path/Symbol:** `crates/biome_service/src/diagnostics.rs:` `TransportError` (:573-584), `Diagnostic for TransportError` (:592-625), `From<TransportError> for WorkspaceError` (:230-234).
**Signature:** `enum TransportError { ChannelClosed, Timeout, SerdeError(String), RPCError(String) }`.
**Data Shape:** two payload-free liveness variants (ChannelClosed, Timeout) and two string-carrying protocol variants (SerdeError carries the serde context + type name from the caller; RPCError carries the server's error message verbatim). Enum is `Debug + Serialize + Deserialize` so it can cross the wire itself.

### Decisive source
```rust
impl Diagnostic for TransportError {
    fn category(&self) -> Option<&'static Category> { Some(category!("internalError/io")) }
    fn severity(&self) -> Severity { Severity::Error }
    // description(): "serialization error: {err}" / ChannelClosed connection-interrupted
    // text / Timeout / RPCError(err) passthrough
    fn tags(&self) -> DiagnosticTags { DiagnosticTags::INTERNAL }
}
impl From<TransportError> for WorkspaceError {
    fn from(err: TransportError) -> Self { Self::TransportError(err) }
}
```

**Flow:** transport implementations produce exactly these variants (`SocketTransport`: serialize fail → SerdeError with `type_name::<P>()`, send fail / dropped oneshot → ChannelClosed, 15s deadline → Timeout, server error field → RPCError(message)); the client's single `?` folds them into `WorkspaceError::TransportError`; rendering marks them INTERNAL io errors regardless of variant.
**Invariant:** the taxonomy is CLOSED at four — transports must classify every failure into one of them rather than inventing new error types, and every variant renders as Severity::Error under category internalError/io with INTERNAL tags (never user-attributable). RPCError passes the server message through unchanged; SerdeError is required to name the Rust type that failed to (de)serialize.
**Probe:** `crates/biome_service/src/diagnostics.rs` `#[cfg(test)]` snapshot tests `transport_channel_closed` (:853-859), `transport_timeout` (:861-864), `transport_rpc_error` (:866-872), `transport_serde_error` (:874-881). CAVEAT: these live in the biome_service lib test target, which does not compile upstream at pin (standing 83-error drift block recorded since pass 16) — tests were READ as specs, not executed; `cargo check -p biome_service --lib` exit 0 executed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "TransportError ChannelClosed Timeout SerdeError RPCError diagnostic", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin: `TransportError.fmt/category/severity/description/message/tags` Methods diagnostics.rs :587-624 resolve line-exact.

## Verdict
Adopt the closed four-variant taxonomy split (liveness vs protocol failures) with uniform internal-io diagnostic identity; adapt category strings and severity policy to your diagnostic system; omit the wire serialization of the error enum if your protocol already has an error frame type. Coverage: `no_recorded_issue` at pin; direct-test runner blocked upstream (recorded above).
