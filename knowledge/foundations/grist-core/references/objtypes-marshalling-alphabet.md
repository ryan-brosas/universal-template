<!-- capsule-v2 -->
# objtypes marshalling alphabet — what crosses the sandbox wire, and what happens on every encode/decode failure?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What is the exact value alphabet crossing the sandbox boundary, and why can encode/decode be treated as total functions?

## Cell-value wire codec
**Path/Symbol:** `sandbox/grist/objtypes.py:encode_object` (:163-220), `decode_object` (:222-257), `RaisedException.encode_args/_fill_from_error/decode_args` (:279-352); TS twin `app/plugin/objtypes.ts:encodeObject/decodeObject` (:157-228).
**Signature:** `encode_object(value) -> primitive | [code, args...]`; `decode_object(encoded) -> value | RaisedException`.
**Data Shape:** codes `R` record(tableId,rowId) · `r` recordset · `D` datetime(ts, zoneName|'UTC') · `d` date(ts) · `E` raised error · `L` list · `l` ReferenceLookup · `O` object (string keys ONLY) · `P` pending sentinel ("Loading...", now only post-migration) · `C` censored sentinel · `U` unmarshallable repr string. Ints must fit signed 32-bit (`is_int_short` :122-123).

### Decisive source
```python
# objtypes.py :169-171, :183-187, :216-220
    if type(value) in (str, float, bool) or value is None:
      return value
...
    elif isinstance(value, int):
      if not is_int_short(value):
        return ['U', str(value)]
      return int(value)   # cast derived ints (e.g. enum.IntEnum) so marshal works
...
  except Exception as e:
    pass
  return ['U', safe_repr(value)]     # encode NEVER raises
```
```python
# objtypes.py :253-257
    elif code == 'U':
      return UnmarshallableValue(args[0])
    raise KeyError("Unknown object type code %r" % code)
  except Exception as e:
    return RaisedException(e)        # decode NEVER raises either
```

**Flow:** primitives pass through unchanged → derived str/float/bool instances are CAST to primitives → bytes decode utf8 → composites map to the code alphabet (AltText encodes as its text; dicts require all-string keys else UnmarshallableError→`['U', repr]`) → any failure degrades to `['U', safe_repr(value)]`. Decode mirrors the alphabet; unknown codes become `RaisedException(KeyError)`. `RaisedException.encode_args` = `[name, message, details?, {"u": user_input}?]` with trailing Nones trimmed (:290-302); `_fill_from_error` unwraps `CellError` chains appending "(in referenced cell T[r].c)" :311-318, special-cases `InvalidTypedValue` to message=typename/details=value (:323-325), and appends `friendly_errors.friendly_message` unless SyntaxError/CircularRefError or a CellError wrap (:319-322); `error.__traceback__` is dropped at construction (:288).
**Invariant:** Both directions are total functions — a port must preserve "encoding failure produces a displayable U-value" and "decoding failure produces an error VALUE", otherwise one hostile cell crashes the engine or the client.
**Probe:** `sandbox/grist/test_objtypes.py:test_encode_object` (:50-64): every encoded form must marshal-round-trip AND its decoded value must re-encode identically — pinned cases include IntEnum→`1`, huge int→`['U', '12345678901234567890']`, FussyFloat whose __float__ raises→`['U', '17.0']`, builtin `len`→`['U', '<built-in function len>']`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", mode: "ids", query: "encode_object decode_object objtypes", limit: 10 });
```

## Verdict
Adopt the total-function failure ladder and the code alphabet with 32-bit int bound. Adapt the concrete codes to your transport if both ends change together (keep E/U semantics). Omit the P/C sentinels if you have no pending/censoring states.
