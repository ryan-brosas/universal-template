<!-- capsule-v2 -->
# Grazie lexicons plane — how is grammar/typo correction shipped as English word-relation data?

**Source:** JetBrains IDE distributions (proprietary distribution); study/reference use only; Codebase Memory `jetbrains-pycharm`. **Question:** What static English-language data files does a grammar-checking engine ship, and what is the plain-text key:→value format for each relation type?

## Connected graph-selected seam
**Path/Symbol:** `plugins/grazie/lib/intellij.grazie.core.jar:en/words/*` (34 files).
**Signature:** `en/words/{replace_US.txt, informal_short_forms.txt, verb_arg_structures.txt, adj_predicative.txt, simple_wording_nominals.txt, adj_attributive.txt, very_abuse.txt, noun_arg_structures.txt, violent_expressions.txt, gendered_expressions.txt, …}`.
**Data Shape:** each file is a flat `key: value` mapping (or bare term) on one line: `replace_US.txt` = British→American word pairs (`aeon: eon`, `aerodrome: airdrome`, `aluminium: aluminum`, `car park: parking lot`); `informal_short_forms.txt` = informal→formal; `verb_arg_structures.txt` / `noun_arg_structures.txt` = subcategorization frames for grammar rules.

### Decisive source
```
en/words/replace_US.txt
aeon: eon
aerodrome: airdrome
ageing: aging
aluminium: aluminum
annexe: annex
car park: parking lot
```

**Flow:** the Grazie engine loads these lexicons at startup → rules (style/grammar/spelling) consult the relevant word file → a flagged span is rewritten with the mapped value. Files are pure data; the rule logic lives in compiled modules.
**Invariant:** every file is a SINGLE relation type with a uniform line grammar — mixing formats would break the loader. The `: ` separator is the field delimiter; bare-term files (no colon) are membership lists.
**Probe:** `unzip -p plugins/grazie/lib/intellij.grazie.core.jar en/words/replace_US.txt | head -3` → `aeon: eon…`; `unzip -l … | grep -c 'en/words/'` → 34.
**Coverage caveat:** resource plane, direct extraction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "grazie grammar spellcheck lexicon", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: per-relation-type lexicon files with uniform `key: value` grammar, loaded as data by a compiled rule engine. Adapt relation vocabulary to your host's grammar model. Omit the lexicons (English data). This is the spelling/grammar twin of the spellchecker-dictionary plane — same data-not-code philosophy, different relation semantics.
