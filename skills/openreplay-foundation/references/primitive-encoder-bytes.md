<!-- capsule-v2 -->
# PrimitiveEncoder byte primitives — how do you encode varints, zigzag ints, and length-prefixed strings into a fixed Uint8Array with honest overflow returns?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** What is the minimal encoder primitive set (and its failure contract) that lets a caller reserve space, back-patch sizes, and never write past the buffer?

## PrimitiveEncoder uint/int/string/skip/set/checkpoint/rewind
**Path/Symbol:** `tracker/tracker/src/webworker/PrimitiveEncoder.ts:PrimitiveEncoder` (:56-130); fallback text-encoder polyfill :1-54.
**Signature:** `uint(value: number): boolean`, `int(value: number): boolean`, `string(value: string): boolean`, `skip(n): boolean`, `set(bytes, offset)`, `checkpoint()`, `rewind(offset, checkpointOffset)`, `flush(): Uint8Array`.
**Data Shape:** One preallocated `Uint8Array(size)`; two cursors — `offset` (write head) and `checkpointOffset` (last known-good boundary). Every primitive returns `this.offset <= this.size` so callers can abort mid-message; `flush()` slices to CHECKPOINT (not offset), so uncheckpointed bytes are silently discarded.

### Decisive source
```ts
uint(value: number): boolean {
    if (value < 0 || value > Number.MAX_SAFE_INTEGER) value = 0   // clamp, not throw
    while (value >= 0x80) {
      this.data[this.offset++] = value % 0x100 | 0x80
      value = Math.floor(value / 128)
    }
    this.data[this.offset++] = value
    return this.offset <= this.size
}
int(value: number): boolean {
    value = Math.round(value)
    return this.uint(value >= 0 ? value * 2 : value * -2 - 1)     // zigzag: n→2n / n→-2n-1
}
rewind(offset: number, checkpointOffset: number): void {
    if (offset > this.offset || checkpointOffset > this.checkpointOffset) return  // forward-only guard
}
flush(): Uint8Array {
    const data = this.data.slice(0, this.checkpointOffset)
    this.reset()
    return data
}
```

**Flow:** caller reserves a size slot with `uint(type)+skip(SIZE_BYTES)` → encodes fields → back-patches the slot via `set()` at a saved absolute offset → `checkpoint()` marks the message committed. On failure anywhere, `rewind(savedOffset, savedCp)` restores both cursors atomically; the forward-only guard makes rewind idempotent and prevents accidentally advancing state.
**Invariant:** Overflow is signaled by return value, NEVER by exception — a partial write can exist in `data` but is unreachable because flush cuts at checkpointOffset. Negative/unsafe ints are clamped to 0 (deterministic garbage beats nondeterministic throw inside a WebWorker hot path). The string path encodes UTF-8 via TextEncoder with a hand-written surrogate-pair fallback (replaces lone surrogates with U+FFFD), then writes varint length BEFORE bytes.
**Probe:** `grep -n 'MAX_M_SIZE' tracker/tracker/src/webworker/BatchBuilder.ts | head -2` from repo root → lines 7 and 141 (verified live); direct tests: `npx jest src/webworker/PrimitiveEncoder.unit.test.ts` in `tracker/tracker` (suite green alongside BatchBuilder battery).
**Retrieve:** search_graph project openreplay query "PrimitiveEncoder uint int string encode" → rank-1 Methods `PrimitiveEncoder.uint :86-96`, `.int :97-100`, Function `encode :7-53` line-exact.

## Verdict
Adopt the boolean-returning primitive set + checkpoint/rewind cursor pair + zigzag mapping as pure codec behavior; adapt the preallocated single buffer to streaming sinks if your transport needs it; omit the IE-era TextEncoder polyfill if your baseline ships TextEncoder.
