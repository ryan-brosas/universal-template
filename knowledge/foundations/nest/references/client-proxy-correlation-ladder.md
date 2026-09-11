<!-- capsule-v2 -->
# Client proxy correlation ladder — how does one client multiplex concurrent requests over a shared broker connection?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you make send() cold and per-subscriber while emit() is hot fire-and-forget, and route each response packet back to exactly one waiter?

## routingMap keyed by random packet id, WritePacket observer ladder
**Path/Symbol:** `packages/microservices/client/client-proxy.ts:ClientProxy` — `send` (85-101), `emit` (110-126), `createObserver` (135-149), `assignPacketId` (159-162), `connect$` (164-176).
**Signature:** `send<TResult, TInput>(pattern: any, data: TInput): Observable<TResult>`; `protected abstract publish(packet: ReadPacket, callback: (packet: WritePacket) => void): () => void`.
**Data Shape:** `routingMap = Map<string /* packet id */, Function /* callback */>`; WritePacket = `{err?, response?, isDisposed?, id?}`.

### Decisive source
```ts
public send(pattern, data) {
  if (isNil(pattern) || isNil(data)) {
    return _throw(() => new InvalidMessageException());
  }
  return defer(async () => this.connect()).pipe(
    mergeMap(() => new Observable((observer) => {
      const callback = this.createObserver(observer);
      return this.publish({ pattern, data }, callback);   // returned fn = teardown
    })),
  );
}
public emit(pattern, data) {
  if (isNil(pattern) || isNil(data)) {
    return _throw(() => new InvalidMessageException());
  }
  const source = defer(async () => this.connect()).pipe(mergeMap(() => this.dispatchEvent({ pattern, data })));
  const connectableSource = connectable(source, { connector: () => new Subject(), resetOnDisconnect: false });
  connectableSource.connect();          // hot immediately
  return connectableSource;
}
protected createObserver<T>(observer: Observer<T>): (packet: WritePacket) => void {
  return ({ err, response, isDisposed }: WritePacket) => {
    if (err) return observer.error(this.serializeError(err));
    else if (response !== undefined && isDisposed) {
      observer.next(this.serializeResponse(response));
      return observer.complete();
    } else if (isDisposed) return observer.complete();
    observer.next(this.serializeResponse(response));
  };
}
protected assignPacketId(packet: ReadPacket): ReadPacket & PacketId {
  const id = randomStringGenerator();
  return Object.assign(packet, { id });
}
```

**Flow:** nil guard ⇒ synchronous cold error observable. `send`: connect runs lazily per subscribe (`defer`, spec-pinned "call connect on subscribe"), then publish stores THIS subscription's callback under a fresh random id; the function publish returns is the unsubscribe teardown (delete correlation). `emit`: connectable connected at call time ("connect immediately", spec-pinned), no correlation slot. Observer ladder: err → error; payload+dispose → next+complete; bare dispose → complete only (an undefined response never emits a value).
**Invariant:** concurrent send() calls share one transport but never share callbacks — correlation is per-packet-id; teardown must remove the slot or late replies leak into nothing (transport-side ignore-by-unknown-id).
**Probe:** `packages/microservices/test/client/client-proxy.spec.ts` ('should call "connect" on subscribe' vs emit 'should call "connect" immediately'; createObserver tests: undefined-response dispose completes without next; assignPacketId adds string id).
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "routingMap assignPacketId createObserver publish", file_pattern: "packages/microservices/client/client-proxy.ts", limit: 8 });
// live @ pin: rank#1 ClientProxy.createObserver 135-149, rank#2 assignPacketId 159-162
```

## Verdict
Adopt the id-keyed correlation map, cold-send/hot-emit split, and the exact three-arm observer ladder (including the `response !== undefined` gate — truthiness would drop falsy payloads); adapt id generation to your runtime's secure randomness; omit RxJS connectable wiring if your reactive core differs.
