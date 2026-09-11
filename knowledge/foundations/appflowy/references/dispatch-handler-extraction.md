<!-- capsule-v2 -->
# Handler extraction state machine — how does a handler's typed parameter get decoded from raw bytes, and where do decode failures surface?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** How does the actix-style `FromAFPluginRequest` extraction work, and why does an extractor error produce a SUCCESS-shaped service response instead of a dispatch error?

## HandlerServiceFuture: Extract → Handle
**Path/Symbol:** `frontend/rust-lib/lib-dispatch/src/service/handler.rs:HandlerServiceFuture` (:106-153) + `data.rs:parse_payload` (:122-139) + tuple extractors (:169-246).
**Signature:** `enum HandlerServiceFuture<H,T,R> { Extract(T::Future, Option<AFPluginEventRequest>, H), Handle(R, Option<AFPluginEventRequest>) }`; extractor bound `T: FromAFPluginRequest` with `T: AFPluginFromBytes` for data types.
**Data Shape:** `Payload::{None, Bytes(Bytes)}`; typed wrapper `AFPluginData<T>(pub T)` derefs to T; up to 5 positional extractors via macro-generated tuples.

### Decisive source
```rust
// handler.rs :128-152 — one polled enum drives the two phases
loop { match self.as_mut().project() {
  HandlerServiceProj::Extract(fut, req, handle) => match ready!(fut.poll(cx)) {
    Ok(params) => { let fut = handle.call(params);
                    let state = HandlerServiceFuture::Handle(fut, req.take());
                    self.as_mut().set(state); },
    Err(err) => { let req = req.take().unwrap();
                  let system_err: DispatchError = err.into();
                  let res: AFPluginEventResponse = system_err.into();
                  return Poll::Ready(Ok(ServiceResponse::new(req, res))); },  // NOTE Ok(...)
  },
  HandlerServiceProj::Handle(fut, req) => {
    let result = ready!(fut.poll(cx));
    let resp = result.respond_to(&req);   // Responder decides body/status
    return Poll::Ready(Ok(ServiceResponse::new(req, resp)));
  }}}
```
```rust
// data.rs :126-133 — None payload + data extractor = UnexpectedNone naming the TYPE
Payload::None => Err(InternalError::UnexpectedNone(format!(
  "Parse fail, expected payload:{:?}", std::any::any::type_name::<T>())).
```

**Flow:** `call` splits the request into (request, payload), starts the type's `from_request` future in the `Extract` state; on success it invokes the handler and transitions to `Handle`, whose output goes through `Responder::respond_to`. Extraction FAILURE short-circuits into a fully-formed error response wrapped in `Ok(ServiceResponse)` — from DispatchService's perspective nothing failed. Multi-arg handlers poll every extractor future concurrently, first error wins.
**Invariant:** Decode errors are RESPONSES (status≠0), never dispatch failures; `Payload::None` meeting a data extractor yields `UnexpectedNone("Parse fail, expected payload:<type>")`; the request object is threaded through both states so responses always carry their originating request. Under default `use_protobuf`, extractable types need `TryFrom<Bytes, Error=ProtobufError>` — plain String is NOT extractable (verified by compile probe; DispatchError itself implements the trait as an any-bytes fallback).
**Probe:** `/tmp/extcollab-af-probe` t03 (None-payload → status≠0 + "payload" in body) and t04 (Bytes payload reaches extractor) executed GREEN at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "HandlerServiceFuture poll Extract Handle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Extract→Handle pin-projected state machine and response-wrapped extraction errors. Adapt the codec trait to your wire format. Omit the 5-tuple machinery if handlers take ≤1 argument.
