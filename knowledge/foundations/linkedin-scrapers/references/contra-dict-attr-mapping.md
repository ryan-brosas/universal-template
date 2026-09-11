<!-- capsule-v2 -->
# ContraDict attribute-dict — how do you expose JSON payloads as both dict and object attributes without breaking dict methods or JSON round-trips?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you build a dict subclass whose items are readable as `obj.key` (for ergonomic scraping of CDP/HTTP JSON), recursive over nested structures, WITHOUT clobbering dict's own method names — and what does the docstring promise that the code does NOT do?

## `__dict__`-aliasing dict subclass + silent-mode key warnings
**Path/Symbol:** `zendriver/core/_contradict.py:ContraDict` (:14-58), `_wrap` (:61-69), `_check_key` (:104-124), `cdict` factory (:97-101); consumers `Browser.info = ContraDict(await self._http.get("version"), silent=True)` (`core/browser.py:136,443`), `Element._attrs = ContraDict(silent=True)` (`core/element.py:62,334,427-442`).
**Signature:** `ContraDict(*args, silent=False)`; `cdict(...)` sugar; `o.x == o['x']` for every non-reserved key.
**Data Shape:** constructor builds a plain `dict` first, then aliases instance `__dict__` to ITSELF via `super().__setattr__("__dict__", self)`, then re-inserts each pair through `_wrap(self.__class__, v)` (Mapping→recurse, Sequence-minus-str/bytes/bytearray/set/tuple→list-of-wrapped, scalars pass). Reserved-name set: items/keys/values/update/clear/copy/fromkeys/get/pop/popitem/setdefault/class, plus any key containing `-` or `.`.

### Decisive source
```python
def __init__(self, *args, **kwargs):
    super().__init__()
    silent = kwargs.pop("silent", False)
    _ = dict(*args, **kwargs)
    super().__setattr__("__dict__", self)   # THE trick: instance __dict__ IS the mapping
    for k, v in _.items():
        _check_key(k, self, False, silent)
        super().__setitem__(k, _wrap(self.__class__, v))   # deep conversion on the way IN
def __setattr__(self, key, value):   # writes go to the dict too
    super().__setitem__(key, _wrap(self.__class__, value))
def __getattribute__(self, attribute):
    if attribute in self:            # data wins over methods
        return self[attribute]
    if not _check_key(attribute, self, True, silent=True):
        return getattr(super(), attribute)
    return object.__getattribute__(self, attribute)
```

**Flow:** aliasing `__dict__` to the mapping itself makes Python's attribute machinery read/write dict entries directly: `obj.x` resolves through membership, so when a payload HAS an `"items"` key, `obj.items` returns YOUR data instead of the bound method — data shadows the method by design, which is exactly why construction warns about reserved names. The reserved-name + hyphen/dot check fires a `UserWarning` naming the offending key unless `silent=True` — zendriver always passes `silent=True` at its two call sites because browser version info and element attribute maps legitimately contain such keys (`http://x` style keys with dots are normal in attr maps). Because insertion routes EVERY value through `_wrap`, nested dicts/lists become ContraDicts recursively, so `info.profile.name` works on HTTP payloads; native `json.dumps/loads` keep working since it really is a dict subclass. NOTE the docstring-vs-code gap: the class docstring promises "all key names converted to snake_case" and "hyphens/dots/whitespace replaced by underscore" — **no code performs any such conversion**; keys stay verbatim. A porter trusting the docstring would corrupt round-tripped payloads.
**Invariant:** (1) attribute access must prefer DATA over dict methods (`if attribute in self` first) — reversing the precedence silently breaks every payload containing "keys"/"values"/"items"; (2) wrap values ON THE WAY IN so nesting is uniform regardless of whether the payload arrived via constructor, `obj[k]=v`, or `setattr`; (3) never mutate keys (the promised normalization doesn't exist) — warn-and-passthrough is the honest contract; (4) always construct from real payloads with `silent=True` in scraper contexts where dotted/hyphenated keys are expected.
**Probe:** no upstream unit test for `_contradict.py` (coverage caveat). Deterministic pins (run from the `zendriver/` package dir, i.e. `…/external/zendriver/zendriver`): `grep -n 'silent' core/browser.py core/element.py` → :443/:62 (both `silent=True`); `grep -n '_warning_names' core/_contradict.py` → :72; live behavior probe (module stubs for `deprecated`, `emoji`, `grapheme`, `asyncio_atexit` per pass-21 recipe — ambient python lacks those deps):
```bash
python3 - <<'EOF'
import sys, types
def _mk(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items(): setattr(mod, k, v)
    sys.modules[name] = mod; return mod
_mk('deprecated', deprecated=lambda *a, **k: (lambda f: f))
_mk('deprecated.sphinx', deprecated=lambda *a, **k: (lambda f: f))
class _E:
  def __getattr__(self, n): return lambda *a, **k: ''
_mk('emoji', emoji=_E())
_mk('grapheme', grapheme=type('g', (), {'count': staticmethod(lambda s: 0)}))
_mk('asyncio_atexit', register=lambda f: f)
sys.path.insert(0, '$REFERENCE_ROOT/external/zendriver')
from zendriver.core._contradict import ContraDict
d = ContraDict(silent=True); d['a'] = 1
assert d.a == 1 == d['a']
print('CONTRADICT_OK')
EOF
```
Graph probe resolves `ContraDict Class 14-58`. NOTE (pass-21 erratum): the docstring's "all key names are converted to snake_case" promise is NOT implemented in code — `_check_key` only warns on `-`/`.`/space keys when not silent.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "ContraDict _check_key _wrap cdict silent", limit: 5 });
```

## Verdict
Adopt the `__dict__`-aliasing kernel for ergonomic JSON-as-object access with recursive wrapping and data-over-methods precedence; adopt the reserved-name warning as the safety net for the inherent collision risk. OMIT the docstring's snake_case claim — it is aspirational, not implemented (record this erratum wherever the class is ported). Coverage: source-pinned only, no upstream unit test (recorded caveat).
