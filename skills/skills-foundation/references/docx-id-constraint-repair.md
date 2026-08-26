<!-- capsule-v2 -->
# docx ID constraint + repair contract — which bases, caps, and stability rules keep paraId/durableId legal?

**Source:** anthropics/skills Apache-2.0/source-available `main@3b3fad96`; Codebase Memory `skills`. **Question:** how are OOXML hex/decimal ID limits enforced and auto-repaired WITHOUT corrupting cross-file references?

## Base-per-file, two caps, stable rename map
**Path/Symbol:** `skills/docx/scripts/office/validators/docx.py` (`DOCXSchemaValidator.validate_id_constraints` :260-314; `repair_durableId` :409-462; `_parse_id_value` :257-258); base repair `validators/base.py` (`repair_whitespace_preservation` :127-160).
**Signature:** `validate_id_constraints() -> bool`; `repair_durableId() -> int` (count of repaired attributes).
**Data Shape:** `w14:paraId` always hex, cap `0x80000000`; `w16cid:durableId` hex cap `0x7FFFFFFF` EXCEPT in `numbering.xml` where the value is DECIMAL with the same cap.

### Decisive source
```python
# :281-287 — numbering.xml is parsed base-10, everything else base-16:
if xml_file.name == "numbering.xml":
    if self._parse_id_value(val, base=10) >= 0x7FFFFFFF:
        errors.append(... "durableId={val} >= 0x7FFFFFFF")
# :438-444 — repair keeps ONE new value per old id across the whole run
# (renames dict), so repeated references stay consistent:
if key not in renames:
    renames[key] = random.randint(1, 0x7FFFFFFE)
value = renames[key]
new_id = str(value) if is_numbering else f"{value:08X}"
```
Repair writes back through `defusedxml.minidom` (`dom.toxml(encoding="UTF-8")`) only when a change was made; unparseable values (`ValueError`) are treated as needing repair.

**Flow:** validate flags over-cap or non-parseable values per file/base → `--auto-repair` assigns each offending id a random in-range replacement ONCE (memoized in `renames`), formats decimal for numbering.xml / zero-padded 8-hex elsewhere → rewrite file → second run finds nothing to do.
**Invariant:** never reformat IDs by re-parsing with the wrong base (a decimal `3000000000` is NOT `0xB2D05E00`); never regenerate per occurrence — one old id maps to exactly one new value or references diverge. Whitespace repair (`xml:space="preserve"` on text-bearing `t/delText/instrText/delInstrText` with leading/trailing whitespace) shares the same minidom write-back path.
**Probe:** put `durableId="3000000000"` in `numbering.xml` and `8FFFFFFF` in document.xml, run `repair_durableId()` twice: first call repairs both (decimal < 2^31 resp. 8-hex), second returns 0. Executed @3b3fad96: repairs=2 then 0 (scratch-docs-p6-probes.py P6a-P6d).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "validate_id_constraints", limit: 5 });
```

## Verdict
Adopt the ID grammar (hex paraId@2^31, durableId@2^31 with numbering.xml decimal) and memoized-repair semantics for any WordprocessingML writer. Adapt caps if targeting newer schema versions. Omit whitespace auto-repair if your pipeline never strips xml:space. Coverage caveat: no upstream tests; behavior executed live at the pin.
