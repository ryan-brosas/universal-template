<!-- capsule-v2 -->
# Object encoder plane — config ladder, format-keeping image codec, and the pickle safety gate

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How does `objects` configuration choose a binary codec, and what guards stand between pickled bytes and execution?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/encoder/factory.py:EncoderFactory.create` (:36-56), `.get` (:17-33); `serialize.py:SerializeEncoder` (:10-28); `image.py:ImageEncoder` (:18-43); pickle gate `src/python/txtai/serialize/pickle.py:allow` (:69-98).
**Signature:** `EncoderFactory.create(encoder) -> Encoder`; `encode(obj) -> bytes`, `decode(data) -> obj`.
**Data Shape:** encoder resolved from Embeddings `"objects"` key: `True` | `"messagepack"` | `"pickle"` | dotted path | bare local name.

### Decisive source
```python
# Return default encoder
if encoder is True:
    return Encoder()
# Supported serialization methods
if encoder in ["messagepack", "pickle"]:
    return SerializeEncoder(encoder)
# Get Encoder instance
return EncoderFactory.get(encoder)()
```
```python
enablepickle = self.allowpickle or os.environ.get("ALLOW_PICKLE", "False") in ("True", "1")
if not enablepickle:
    raise ValueError(("Loading of pickled index data is disabled. ... Set the env variable `ALLOW_PICKLE=True` to enable ..."))
```

**Flow:** `True` → base Encoder (identity encode; decode wraps bytes in BytesIO, None-safe) → named serializers hit SerializeEncoder over the shared SerializeFactory → anything else resolves: bare name expands to `<name>Encoder` inside the encoder package (`ImageEncoder`), dotted paths resolve any external class — resolution failure surfaces as ImportError at index time. ImageEncoder re-saves with `format=obj.format, quality="keep"` so PNGs stay PNGs; decodes empty bytes to None. Encode happens in loadobject only when `self.encoder` is set; decode happens at query result mapping and during reindex streaming.

**Invariant:** The pickle gate is fail-closed and env-overridable with an explicit warning — a port that swaps pickle for cloudpickle must keep BOTH the default-deny posture AND the remediation-message contract (tests assert against this behavior via ALLOW_PICKLE patching). Encoder choice is stored per index config; changing encoders after indexing corrupts reads (bytes interpreted by the wrong codec), which is why Embeddings.reindex force-preserves `objects` across configure().

**Probe:** `test/python/testdatabase/testencoder.py` whole file (:22-171): testDefault (BytesIO roundtrip), testImages (PIL Image out of SQL search), testInvalid (`"pprint.pprint"` → ImportError at index), testPickle (@patch ALLOW_PICKLE=True list roundtrip), testReindex/testReindexFunction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "EncoderFactory SerializeEncoder ImageEncoder objects create", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: all six encoder symbols returned line-exact (:17-56 factory, :15-28 serialize, :23-43 image).

## Verdict
Adopt the three-arm factory + fail-closed pickle gate + format-keeping image codec; adapt the serializer allowlist to your stack (e.g. add arrow); omit image special-casing if objects are opaque bytes. Coverage caveat: testInvalid's ImportError depends on Resolver behavior — verified by direct read of both factories. Cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
