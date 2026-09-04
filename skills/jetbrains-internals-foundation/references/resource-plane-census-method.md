<!-- capsule-v2 -->
# resource-plane-census-method — how do you prove WHICH resource planes an installed IDE ships before mining any of them?

**Source:** JetBrains installed distributions (proprietary), all 15 installs, census executed at pinned builds (see work record [DONE:128] for numbers). **Question:** What deterministic sweep replaces guessing about jar-internal resources across a cluster?

## Zip-sweep census: per install, count resource dirs across every jar
**Path/Symbol:** glob ladder `lib/*.jar + lib/ext/*.jar + plugins/*/lib/*.jar + plugins/*/lib/modules/*.jar + plugins/*/*/lib/**/*.jar`; per jar count members by top dir: `inspectionDescriptions/`, `intentionDescriptions/`, `messages/*.properties`, `fileTemplates/`, `liveTemplates/`, `postfixTemplates/`, `tips/`, `colors/`.
**Signature:** census script (kept at `.pi/work/foundations-deep-farm/scratch-jb-resource-census.py`) prints `<ide>: jars=N insp=N inten=N msgs=N` — one line per install, fully re-runnable.
**Data Shape (262-train snapshot):** full installs cluster tightly — insp 12.2k–13.1k, inten 3.9k–4.8k, msgs 4.5k–4.8k; dataspell (older 261 train) ~11.6k; mps ~1k; air exactly 0 with jars=0 (no lib jars at all).

### Decisive source
```python
# decisive excerpt — the counting rule that makes cross-IDE claims checkable
for j in jars:
    z = zipfile.ZipFile(j)
    names = z.namelist()
    i = sum(1 for n in names if n.startswith('inspectionDescriptions/'))
    m = sum(1 for n in names if n.startswith('messages/') and n.endswith('.properties'))
```
Result table (pycharm→mps): 12742/4547/4730 · 12614/4433/4635 · 12925/4799/4759 · 12717/4608/4630 · 12816/4676/4640 · 12713/4592/4641 · 13061/4764/4652 · 12978/4682/4593 · 12172/3935/4559 · 12647/4483/4742 · 11642/3973/4216 · 0/0/0 · 1059/573/192.

**Flow:** run census FIRST on a fresh cluster → tight ranges prove shared platform planes (mine once, cite richest instance) → outliers become per-product capsules (datagrip's small inspection set = DB-focused surface) → zeros become omit-notes (air) or separate-taxonomy notes (thin-vs-full-layout-taxonomy).
**Invariant:** the census counts PATH PREFIXES, not content — it is a MAP, not evidence about semantics; every semantic claim still needs the decisive in-file read from the specific capsule. Re-run after ANY build bump before citing numbers.
**Probe:** `python3 .pi/work/foundations-deep-farm/scratch-jb-resource-census.py | md5sum` reproduces the recorded table (numbers may drift only with new installs); single-IDE spot-check: `unzip -l pycharm/plugins/python-ce/lib/modules/intellij.python.psi.impl.jar | grep -c inspectionDescriptions` → 98 lines (97 files + header).
**Retrieve:** not a graph seam; keep the script path pinned so later passes re-execute rather than re-derive.

## Verdict
Adopt: prefix-prefix census as the standard first move for any binary distribution cluster — it converts "what's in there?" from folklore to a re-runnable table. Adapt prefix list to your domain. Omit content parsing from the census itself. Caveat: this method capsule cites the others; if planes are added later, extend the prefix set and re-record.
