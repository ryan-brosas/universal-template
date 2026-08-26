<!-- capsule-v2 -->
# Office toolkit triplication — when can a porter treat the three vendored copies as one?

**Source:** anthropics/skills Apache-2.0/source-available `main@3b3fad96`; Codebase Memory `skills`. **Question:** the docx/pptx/xlsx skills each vendor a full `scripts/office` toolkit — which copies are interchangeable, and what does each skill actually ship?

## One byte-identical kernel, unpruned vendor sets
**Path/Symbol:** `skills/{docx,pptx,xlsx}/scripts/office/**` (whole toolkit, 49 shared files).
**Signature:** n/a (file-level identity contract).
**Data Shape:** every skill ships ALL of: `validators/{base,docx,pptx,redlining}.py`, `helpers/{__init__,pptx_chart,pptx_slide,pptx_theme}.py`, `validate.py`, `soffice.py`, plus XSD corpora (`ISO-IEC29500-4_2016/`, `ecma/`, `mce/`, `microsoft/wml-*`). Nothing is pruned per consumer.

### Decisive source
```text
md5 census @ 3b3fad96 (scratch-docs-p6-census.py): all 49 files shared across the
three skills are BYTE-IDENTICAL (single md5 each), including soffice.py,
validate.py, every validator, every helper, and every XSD. Graph agrees:
194 SIMILAR_TO edges over 66 distinct symbols, 64 present in all three skills
(validators.base ×17, validators.pptx ×10, redlining ×9, docx-validator ×9,
helpers.pptx_chart ×8 ...). Zero divergent copies.
```

**Flow:** any skill entry point (`docx` scripts, `pptx` scripts, `xlsx` recalc) imports its LOCAL copy `from helpers import ...` / `from validators import ...` — the packages resolve relative to that skill's own `scripts/office` dir, never across skills.
**Invariant:** fix a bug in one copy and you MUST replicate it in all three (they are clones today; nothing keeps them in sync upstream except manual discipline). When porting, vendor ONE copy and share it — do not fork per-consumer unless you also inherit the drift risk.
**Probe:** `for f in $(cd skills/docx/scripts/office && find . -type f -name '*.py'); do n=$(md5sum skills/{docx,pptx,xlsx}/scripts/office/$f | awk '{print $1}' | sort -u | wc -l); echo "$n $f"; done | sort -rn | head -3` (every line starts with `1` = identical; executed @3b3fad96, all lines `1` incl. `__pycache__` twins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "BaseSchemaValidator", limit: 10 });
```

## Verdict
Adopt the single-kernel insight: treat `scripts/office` as ONE portable unit (validators + helpers + schemas + CLI) rather than three per-skill modules. Adapt the import style to your host layout (here it relies on running from inside `scripts/office`). Omit per-skill divergence handling — none exists at this pin. Coverage caveat: no upstream test pins the identity; the md5 census IS the evidence.
