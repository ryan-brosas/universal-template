<!-- capsule-v2 -->
# Vector encode int32 decode bug — Which latent upstream defect must a porter NOT copy?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** encode_vector supports FLOAT32/INT32 — is decode symmetric, and why does it matter to a port?

## encode_vector / decode_vector
**Path/Symbol:** `chromadb/ingest/__init__.py:encode_vector` (:15-23), `decode_vector` (:26-34).
**Signature:** `decode_vector(vector: bytes, encoding: ScalarEncoding) -> Vector`.
**Data Shape:** WAL stores raw `.tobytes()` blobs plus the encoding string; readers reconstruct via `np.frombuffer`.

### Decisive source
```python
def decode_vector(vector: bytes, encoding: ScalarEncoding) -> Vector:
    """Decode a byte array into a vector"""
    if encoding == ScalarEncoding.FLOAT32:
        return np.frombuffer(vector, dtype=np.float32)
    elif encoding == ScalarEncoding.INT32:
        return np.frombuffer(vector, dtype=np.float32)   # <-- dtype MISMATCH
    else:
        raise ValueError(f"Unsupported encoding: {encoding.value}")
```

**Flow (live-verified):** INT32 round-trip returns float32 view of the same 4-byte-per-element buffer. For whole non-negative int32 values values survive because float32 exactly represents small ints, but (a) large magnitudes (>2^24) silently lose precision and (b) downstream code reading `Vector` assumes floats. The asymmetry is one-directional: encode is correct, decode mislabels.
**Invariant:** A codec pair MUST be dtype-symmetric; if you inherit this file, fix INT32 decode rather than replicate.
**Probe:** `/tmp/chroma-p1/probe_battery.py` vec.int32_float_bug asserts the bug EXISTS at this pin (`i32.dtype.name == 'float32'`) so drift in either direction is caught; vec.f32_roundtrip checks the healthy path (both GREEN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "encode_vector decode_vector ScalarEncoding frombuffer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt FLOAT32 path as-is; FIX INT32 decode in any port (upstream may repair later — re-check on re-entry past pin); omit other encodings (unsupported here by design).
