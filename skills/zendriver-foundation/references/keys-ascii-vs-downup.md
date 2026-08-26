<!-- capsule-v2 -->
# keys-ascii-vs-downup — how text becomes CDP key events, and why CHAR vs DOWN_AND_UP matters

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** When does send_keys emit bare `char` events vs full down/up sequences with modifiers, and how are shifted keys normalized?

## Graphemes in, payloads out; emoji force CHAR
**Path/Symbol:** `zendriver/core/keys.py:KeyEvents` (:56-501) — `from_text` (:503-543), `_normalise_key` (:197-245), `to_down_up_sequence` (:449-501), maps (:87-129); consumed by `Element.send_keys` (`element.py:761-782`).
**Signature:** `from_text(cls, text: str, ascii_keypress: KeyPressEvent) -> List[Payload]`; `to_cdp_events(self, key_press_event, override_modifiers=None)`.
**Data Shape:** Payload TypedDict: `{type_, modifiers, text, key, code, windows_virtual_key_code, native_virtual_key_code}`; `KeyPressEvent.CHAR = "char"` (ASCII-only), `DOWN_AND_UP` (non-standard compound), modifier bitmask Alt=1 Ctrl=2 Meta=4 Shift=8.

### Decisive source
```python
# from_text: grapheme-aware split; emoji bypass key-code lookup entirely
for grapheme_char in grapheme.graphemes(text):
    ...
    all_payload.extend(key_events.to_cdp_events(
        KeyPressEvent.CHAR if emoji.is_emoji(grapheme_char) else ascii_keypress))
# _normalise_key: shifted char → base char + Shift flag
if key in self.NUM_SHIFT:
    modifiers |= KeyModifiers.Shift
    lowercase_key = str(self.NUM_SHIFT.index(key))   # ")!@#$%^&*(" → 0-9
elif KeyEvents.is_english_alphabet(key) and key.isupper():
    modifiers |= KeyModifiers.Shift
    lowercase_key = key.lower()
```
and the ordered modifier envelope (:473-500): modifier downs accumulate `current_modifiers |= flag`, main key down carries the full mask, modifier ups strip `current_modifiers &= ~flag` in reverse order, main key up last.

**Flow:** `send_keys(text)` focuses via JS then dispatches each payload as one `input.dispatch_key_event`. Strings go through `from_text`; a lone `SpecialKeys` uses DOWN_AND_UP; raw payload lists pass through untouched. Lookup ladder for codes: letters→`Key{A}`+ord, digits/NUM_SHIFT→`Digit{n}`, `\n\r`→Enter(13), `\t`→Tab(9), space→32, punctuation via SPECIAL_CHAR_MAP (e.g. `;`→Semicolon/186) and its shift-twin map; unknown (non-English/emoji) yields `(None, None)` which forces CHAR mode.
**Invariant:** live-executed probe this pass: sending `"aA \n"` produced input values `a`, `aA`, `aA ` — trailing newline was delivered as an Enter *key* event and did NOT add a character to the single-line input; only value-changing chars hit `input`. Ports assuming every keystroke mutates `.value` will miscount events.
**Probe:** direct tests: `tests/core/test_keyinputs.py::test_visible_events` (:7) and `::test_escape_key_popup` (:46); fixture `tests/sample_data/special_key_detector.html`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "KeyEvents from_text grapheme", limit: 5 });
```

## Verdict
Adopt the grapheme loop + shift normalization tables verbatim; adapt key codes only for non-US layouts; keep the emoji→CHAR escape hatch or unicode input breaks.
