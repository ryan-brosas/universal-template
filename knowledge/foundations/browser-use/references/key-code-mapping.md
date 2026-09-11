<!-- capsule-v2 -->
# Keyboard event code mapping — how do you translate key names into CDP Input domain codes?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** what is the contract for converting 'Enter'/'a'/';' into (code, windowsVirtualKeyCode) pairs CDP dispatchKeyEvent accepts?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/actor/utils.py` whole (176L) — `Utils.get_key_info` (:8) + module-level backward-compat alias (:164).
**Signature:** `get_key_info(key: str) -> tuple[str, int | None]`.

### Decisive source
```python
# Explicit table covers: navigation (Backspace..Delete), modifiers, F1-F24,
# numpad, lock keys, OEM punctuation WITH symbol aliases (';' -> ('Semicolon', 186)),
# media/browser keys.
if key in key_map: return key_map[key]
# Dynamic single-char fallback:
if len(key) == 1:
    if key.isalpha():   return (f'Key{key.upper()}', ord(key.upper()))  # A-Z VK 65-90
    elif key.isdigit(): return f'Digit{key}', ord(key)                  # 0-9 = ASCII 48-57
return (key, None)  # unknown: pass through as code, NO virtual key code

# Modifier nuance (probe-verified): the BARE name normalizes to the Left code,
# but an EXPLICIT Right suffix keeps its own location-specific code with the
# SHARED Windows VK — do NOT collapse Right to Left:
#   'Shift' -> ('ShiftLeft', 16)      'ShiftRight' -> ('ShiftRight', 16)
#   'Meta'  -> ('MetaLeft', 91)       'MetaRight'  -> ('MetaRight', 92)
```

**Flow:** named keys hit the static table → single characters synthesize `Key<X>`/`Digit<N>` codes with ASCII ordinal VK codes → anything else passes the raw name with `None` VK (CDP tolerates missing keyCode).
**Invariant:** bare modifier names normalize to Left codes while explicit `*Right` names keep their own code with the shared Windows VK — collapsing Right to Left breaks location-aware shortcuts; digit VK codes equal their ASCII ordinals while letters use UPPERCASE ordinals — mixing these up produces shifted/unshifted text bugs; unknown keys degrade to `(key, None)` rather than raising so exotic layouts still type.
**Probe:** deterministic source probe (coverage caveat: no dedicated test file; table pinned by citation :22-:145 and consumed by actor keyboard paths).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "get_key_info windowsVirtualKeyCode key_map Utils", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mapping table + dynamic single-char synthesis + left-modifier collapse verbatim; extend the table for non-US layouts; omit the class wrapper if your host prefers a bare function.
