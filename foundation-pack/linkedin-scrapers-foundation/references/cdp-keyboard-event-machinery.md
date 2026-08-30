<!-- capsule-v2 -->
# CDP keyboard-event machinery — how do you turn a string (incl. emoji, shift-chars, and Ctrl+key combos) into a correct CDP key-event sequence?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** what is the correct ordering and key-code mapping for typing text and pressing key combos over CDP, including non-ASCII and shifted characters?

## Grapheme-split → key-code lookup → modifier down/main/down-up ordering
**Path/Symbol:** `zendriver/core/keys.py:KeyEvents` (:56-595), `Element.send_keys` (`core/element.py:761-782`).
**Signature:** `KeyEvents.from_text(text, ascii_keypress)`; `KeyEvents.from_mixed_input(sequence, ascii_keypress=DOWN_AND_UP)`; `KeyEvents(key, modifiers).to_cdp_events(kind)`; `Element.send_keys(text|SpecialKeys|list[Payload])`.
**Data Shape:** CDP `Input.dispatchKeyEvent` payloads carry `type_` (keyDown/keyUp/char/rawKeyDown), `modifiers` bitmask (Alt=1/Ctrl=2/Meta=4/Shift=8), `text`, `key`, `code`, `windows_virtual_key_code`, `native_virtual_key_code`. Key-code tables: `NUM_SHIFT=")!@#$%^&*("` (shifted digit chars), `SPECIAL_CHAR_MAP` (punct → code/name), `SPECIAL_CHAR_SHIFT_MAP` (shifted punct → base).

### Decisive source
```python
# from_text: split by GRAPHEME (not char) so emoji/combining chars stay whole
for grapheme_char in grapheme.graphemes(text):
    key_events = cls(SpecialKeys.ENTER) if grapheme_char in "\n\r" else cls(grapheme_char)
    all_payload.extend(key_events.to_cdp_events(
        KeyPressEvent.CHAR if emoji.is_emoji(grapheme_char) else ascii_keypress))
# to_down_up_sequence: modifier-down → main-down → modifier-up(reverse) → main-up
for modifier_key, modifier_flag in modifier_events:
    current_modifiers |= modifier_flag
    events.append(modifier_key._to_basic_event(KeyPressEvent.KEY_DOWN, current_modifiers))
if not is_modifier_key:
    events.append(self._to_basic_event(KeyPressEvent.KEY_DOWN, current_modifiers))
for modifier_key, modifier_flag in modifier_events:      # reverse order on the way up
    current_modifiers &= ~modifier_flag
    events.append(modifier_key._to_basic_event(KeyPressEvent.KEY_UP, current_modifiers))
```

**Flow:** `from_text` walks graphemes (emoji-safe), mapping `\n`/`\t`/space to special keys and everything else to a char event (emoji → CHAR, ASCII → the caller's chosen kind). `_normalise_key` converts a shifted char to its base + sets the Shift modifier (`"A"`→`a`+Shift, `"!"`→`1`+Shift, `":"`→`;`+Shift). `to_down_up_sequence` emits modifier-down events with ACCUMULATED modifiers, then the main key down, then modifier-ups in REVERSE order (decrementing the mask), then the main key up. `from_mixed_input` accepts strings (char-by-char), `SpecialKeys`, and `(key, modifiers)` tuples (e.g. `("a", Ctrl)` = Ctrl+A).
**Invariant:** modifier keys are pressed down BEFORE the main key and released AFTER it, and the modifier bitmask is ACCUMULATED as each modifier goes down and DECREMENTED as each comes up — the mask at every event reflects exactly which modifiers are currently held. Emoji must go through the `char` event (they have no key code); non-ASCII that isn't emoji also degrades to CHAR. This is the precise CDP counterpart to the ghost-cursor-click-ladder and selenium-click-finder-ladder already in this suite — the input-event layer under every form-fill.
**Probe:** REAL tests — `tests/core/test_keyinputs.py` (2 live tests): `test_visible_events` types a mixed sequence incl. Ctrl+A/C/V + emoji into a contenteditable and asserts the exact resulting DOM (4 children, pasted text intact), `test_escape_key_popup` sends `SpecialKeys.ESCAPE` and asserts the popup closed. Deterministic pin (anchored at the `zendriver/` package dir): `grep -n 'NUM_SHIFT = ' core/keys.py` → :87.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "KeyEvents from_mixed_input to_down_up_sequence modifiers", limit: 5 });
```

## Verdict
Adopt: grapheme-split typing, base-key + Shift normalization, and modifier-down/main/modifier-up(reverse) ordering with accumulated masks. Adapt the key-code tables to your target keyboard layout. Omit the `emoji`/`grapheme` dependency if you don't need unicode. Coverage: directly test-pinned (2 live tests).
