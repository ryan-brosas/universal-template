<!-- capsule-v2 -->
# FFI byte protocol — how do Dart and Rust exchange requests and responses through ports with a length prefix?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What is the exact wire format across the dart-ffi boundary, and which side owns each buffer?

## FFIRequest/FFIResponse + four-byte big-endian prefix
**Path/Symbol:** `frontend/rust-lib/dart-ffi/src/lib.rs` (`init_sdk` :113-171, `async_event` :173-186, `post_to_flutter` :256-275) + `dart-ffi/src/c.rs:extend_front_four_bytes_into_bytes`.
**Signature:** `pub extern "C" fn async_event(port: i64, input: *const u8, len: usize)`; `async fn post_to_flutter(response: AFPluginEventResponse, port: i64)`; `fn extend_front_four_bytes_into_bytes(bytes: &[u8]) -> Vec<u8>`.
**Data Shape:** Requests arrive as protobuf-encoded `FFIRequest{event, payload}`; responses leave as protobuf `FFIResponse`, prefixed by a u32 big-endian LENGTH so the Dart side can slice the buffer.

### Decisive source
```rust
// c.rs — every response crosses the boundary length-prefixed
pub fn extend_front_four_bytes_into_bytes(bytes: &[u8]) -> Vec<u8> {
  let mut output = Vec::with_capacity(bytes.len() + 4);
  let mut marker_bytes = [0; 4];
  BigEndian.write_u32(&mut marker_bytes, bytes.len() as u32);
  output.extend_from_slice(&marker_bytes);
  output.extend_from_slice(bytes);
  output
}
```
```rust
// lib.rs :258-265 — allo_isolate posts the prefixed bytes to the Dart SendPort
let isolate = allo_isolate::Isolate::new(port);
match isolate.catch_unwind(async {
  let ffi_resp = FFIResponse::from(response);
  ffi_resp.into_bytes().unwrap().to_vec()
}).await { Ok(_) => ..., Err(err) => error!("[FFI]: allo_isolate post failed: {:?}", err) }
```

**Flow:** Dart calls `async_event(port, ptr, len)` → `FFIRequest::from_u8_pointer` decodes → `DART_APPFLOWY_CORE.dispatch` pushes onto an unbounded mpsc → the dedicated LocalSet thread's Runner spawns handling and registers a callback that posts the encoded response back through `allo_isolate::Isolate(port)`. `init_sdk` is idempotent per-process: it closes the previous core's DB before rebuilding (re-login path), and clamps app_version to ≥0.5.8. Notification and log streams use separate ports registered via `set_stream_port` / `set_log_stream_port`.
**Invariant:** The 4-byte length prefix is part of EVERY response (Dart slices by it); Rust leaks response buffers deliberately (`forget_rust`) and Dart frees them after slicing — "fixing" the leak without changing ownership corrupts the protocol; panics inside response encoding are caught by `catch_unwind` so a bad payload degrades to an error log instead of crashing the isolate.
**Probe:** Source-pinned byte-exact at HEAD (`extend_front_four_bytes_into_bytes`, `post_to_flutter`). Retrieval rank#1 line-exact for both symbols.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "extend_front_four_bytes_into_bytes post_to_flutter isolate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the length-prefixed port protocol and one-thread LocalSet host. Adapt codec (protobuf here) freely as long as both sides agree on prefixing. Omit sync_event (unimplemented stub at this pin).
