<!-- capsule-v2 -->
# val_json_bytes ladder — how does a bytes field decode from JSON text, and why does base64 accept BOTH alphabets?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** A porter implementing JSON-side bytes validation must reproduce the config key, the zero-copy default, and the dual-alphabet base64 fallback exactly.

## `val_json_bytes` → shared BytesMode; Utf8 borrows; Base64 falls back URL-safe→STANDARD only on `/`|`+` bytes; all failures are `bytes_invalid_encoding`
**Path/Symbol:** `src/validators/config.rs:ValBytesMode` (:74-113) + padding-indifferent engines (:16-23); consumers = each backend's `validate_bytes` (input_json.rs / input_python.rs / input_string.rs).
**Signature:** `pub fn deserialize_string<'py>(self, s: &str) -> Result<EitherBytes<'_, 'py>, ErrorType>`.
**Data Shape:** `ValBytesMode { ser: BytesMode }` reuses the SERIALIZERS' `BytesMode::{Utf8, Base64, Hex}` enum; output is `EitherBytes` (Cow-borrowed or owned Vec).

### Decisive source
```rust
BytesMode::Base64 => URL_SAFE_OPTIONAL_PADDING.decode(s)
    .or_else(|err| match err {
        DecodeError::InvalidByte(_, b'/' | b'+') => STANDARD_OPTIONAL_PADDING.decode(s),
        _ => Err(err),
    })
    .map_err(|err| ErrorType::BytesInvalidEncoding { encoding: "base64".to_string(), encoding_error: err.to_string(), context: None }),
```

**Flow:** config dict key `val_json_bytes` parsed once at build (`from_config`, :80-87), defaulting to BytesMode::Utf8. At validate time a JSON string reaches `deserialize_string`: Utf8 returns `Cow::Borrowed(s.as_bytes())` — ZERO copy; Hex uses `hex::decode`; Base64 tries the URL_SAFE alphabet first and retries STANDARD only when an invalid byte is literally `/` or `+` (i.e., the input looks standard-alphabet), both engines configured `DecodePaddingMode::Indifferent`. Every decode failure becomes `bytes_invalid_encoding` carrying `{encoding, encoding_error}`. StringMapping's `validate_bytes` routes through the same method (input_string.rs:115-127), so string-mode bytes fields honor `val_json_bytes` too.
**Invariant:** acceptance is ALPHABET-DRIVEN, not strictness-driven — url-safe `_`/`-` and standard `/`/`+` encodings of the SAME bytes both decode under one mode, and padding is optional. A port that picks a single base64 alphabet breaks round-trips against the other ecosystem half; one that surfaces raw decoder errors instead of `bytes_invalid_encoding` breaks the error contract.
**Probe:** direct probe Q7 executed live @ pin byte-matching tests/test_json.py::test_json_bytes_base64_round_trip (:386-404): validator(bytes_schema, CoreConfig(val_json_bytes='base64')) decodes BOTH `b'"2AfBVHgkkUYl8/NJythADO7Dq/9/083N+cIQ5KGwMWU="'` (standard) and its `'_'`/`'-'` url-safe twin to identical bytes; `validate_json('"wrong!"')` raises with errors()[0]['type'] == 'bytes_invalid_encoding'.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "cache_str string cache mode maybe_cached_str config", limit: 10 });
// live run this pass: ValBytesMode.deserialize_string ranks inside this band (config.rs:89-113) next to the serializers' BytesMode.bytes_to_string mirror (serializers/config.rs:319-329) — open by qn to separate the validation vs serialization halves
```

## Verdict
Adopt the three-mode enum sharing between ser/de sides plus the two-engine fallback predicate verbatim; adapt error payloads to your host's error type while keeping the `{encoding, encoding_error}` pair; omit Hex if your schema language lacks it (but keep the enum slot for wire parity). Coverage: validators/config.rs + tests/test_json.py no_recorded_issue @ gen 2026-08-25T20:09:30Z.
