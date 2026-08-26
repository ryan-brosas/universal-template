<!-- capsule-v2 -->
# Socket transport LSP framing — how are messages framed and null-ish responses recovered on a raw socket?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** What is the minimal robust wire framing for a JSON-RPC peer, including the response-shape edge cases?

## Header loop + result/error XOR + synthesized null
**Path/Symbol:** `crates/biome_cli/src/service/mod.rs:` `read_message` (:313-372), `write_message` (:400-421), `read_task` response match (:279-309), `JsonRpcRequest`/`JsonRpcResponse`/`JsonRpcError` (:423-448), `TransportHeader` (:450-486).
**Signature:** `async fn read_message<R: AsyncBufRead + Unpin>(socket_read: R) -> Result<Vec<u8>, Error>`; `async fn write_message<W: AsyncWrite + Unpin>(socket_write: W, message: Vec<u8>) -> Result<(), Error>`.
**Data Shape:** headers parsed via `FromStr for TransportHeader` → `ContentLength(usize) | ContentType | Unknown(String)`; response struct is `#[serde(deny_unknown_fields)] { jsonrpc (dead), id, result: Option<Box<RawValue>>, error: Option<JsonRpcError> }`.

### Decisive source
```rust
match socket_read.read_line(&mut line).await...? {
    0 => bail!("the connection to the remote workspace was unexpectedly closed"),
    2 => { if line != "\r\n" { bail!("unexpected byte sequence ..."); } break; }
    _ => { /* parse header; Content-Length sets length; ContentType ok; Unknown eprintln'd */ }
}
// ... then read_exact(vec![0u8; length]) or error "missing the Content-Length header"
let response = match (response.result, response.error) {
    (Some(result), None) => Ok(result),
    (None, Some(err)) => Err(TransportError::RPCError(err.message)),
    // Both None = a null-ish result; synthesize a "null" RawValue
    // SAFETY: Calling `to_raw_value` with a static "null" JSON Value will always succeed
    (None, None) => Ok(to_raw_value(&Value::Null).unwrap()),
    _ => Err(TransportError::SerdeError(message)),  // both set = invalid
};
```

**Flow:** read header lines until the bare `\r\n` terminator → require Content-Length → read exactly that many bytes as the body. Writes mirror it: `Content-Length: N\r\n`, `Content-Type: application/vscode-jsonrpc; charset=utf-8\r\n`, blank line, body, flush. In `read_task`, a fulfilled channel sends the XOR-classified outcome; unknown headers are skipped with an eprintln, never fatal.
**Invariant:** a 0-byte read IS connection close (not EOF-retry); a missing Content-Length is an error, not a zero-length message; `(Some, Some)` is invalid and becomes SerdeError; `(None, None)` must NOT fail deserialization of `R: DeserializeOwned` downstream — it is normalized to JSON null so unit-returning methods (`close_file`, `update_module_graph`) deserialize cleanly. `deny_unknown_fields` keeps protocol drift loud.
**Probe:** no dedicated upstream test drives `read_message`/`write_message` at pin (recorded caveat — exercised end-to-end by daemon integration only); compile gate `cargo check -p biome_cli --lib` exit 0 executed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "Content-Length header transport jsonrpc response read write socket", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin: the `Transport.request` TS twin cluster and Rust `SocketTransport.request` resolve; note the framing helpers themselves are free functions surfaced through their caller's neighborhood.

## Verdict
Adopt the header/body framing contract (0-byte=closed, required Content-Length, skip-unknown-headers) and the four-way result/error XOR with null synthesis; adapt content-type validation to your protocol versioning; omit the SAFETY null trick only if your deserializer accepts absent fields natively. Coverage: `no_recorded_issue` at pin; source read whole.
