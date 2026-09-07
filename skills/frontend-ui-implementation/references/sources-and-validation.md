# Sources and Behavioral Validation

## Source boundary

The primary source is `100 UI-UX Tips & Tricks.pdf`, titled *100 Practical UI/UX Tips*, 108 pages, creator metadata Victor Ponamariov, created in 2021. Pages 8–107 contain the 100 tips; page 108 is the afterward. The complete text was extracted and audited page by page.

The source mixes durable frontend principles, approximate defaults, opinionated patterns, and accessibility claims. This skill preserves concrete values so implementers can use them, while classifying them correctly:

- PDF line-height bands: headings **1–1.4**, general text **1.3–1.6**, with **16px × 1.5 = 24px** as its example.
- PDF line-length references: **45–75 characters** and **50–60 characters**.
- PDF modular-scale examples: **16px base**, ratios **1.25**, **1.414**, and **1.5**.
- PDF page 49 advocates larger landing-page text but provides **no numeric font size** in its text or illustration; no exact value may be attributed to that page.
- PDF animation bands: **<100ms**, **100–200ms**, **200–300ms**, and **>300ms**.
- PDF heuristics: expose roughly **5–7** dropdown choices; group pie charts after roughly **5–6** slices; examples around **0.2s** loads and **<0.5s** before a loader.

These are source recommendations, not WCAG requirements. Current project standards, actual font/content behavior, platform conventions, security, and the applicable accessibility target can override them. The skill explicitly rejects literal 7±2 item limits, a universal pure-black ban, universal autofocus, fake progress, and content removal solely to fit.

Normative accessibility claims belong to `wcag-accessibility-practices` and current W3C guidance. `frontend-markup-practices` owns generic static HTML/CSS conventions. This skill owns the production UI-detail implementation layer.

## Coverage proof

`pdf-coverage-matrix.md` maps every page from 8 through 107, exactly once, to one implementation branch and one verification hook. Its embedded mechanical check must report `PDF COVERAGE: 100/100`.

## Behavioral rubric

A response passes at 5/6 when it:

1. Loads the relevant branch rather than improvising from the entry file.
2. Gives concrete CSS/HTML/component behavior, not only UX advice.
3. Preserves exact relevant PDF values and labels them heuristics/defaults rather than standards.
4. Covers responsive, content-extreme, interaction, async/error, and accessibility behavior relevant to the task.
5. Uses project truth first and does not invent a design file, research result, or completed test.
6. Defines executable verification and does not solve fit by shrinking text, hiding meaning, or removing task-critical data. Item 6 is mandatory.

## RED and GREEN record

The demonstrated RED was direct user feedback: the earlier `ui-ux-iteration-loop` synthesis omitted usable font-size and related frontend implementation principles even though the PDF contained concrete values. The fix is a separate retrieval surface, not more research-loop prose.

Two read-enabled probes with different model families were run after implementation:

- **Typography/pricing scenario**, `cursor/gemini-3.1-pro`: provided `rem`/`clamp()` CSS, 16px base, 1.0–1.4 and 1.3–1.6 leading bands, 16×1.5=24px example, 45–75/50–60 character measures, modular ratios, stable loading geometry, responsive states, PDF-vs-WCAG classification, and explicit verification. **6/6.**
- **Checkout remediation scenario**, `cursor/claude-sonnet-4-6@200k`, high thinking: restored labels/native file semantics, corrected OTP completion behavior, stable loading controls, scoped loader timing, critical mobile data, icon names, reduced motion, async state models, and the PDF’s timing/count bands as heuristics. **6/6.**

Reproduce from the repository root with `pi --no-session --tools read --skill skills/frontend-ui-implementation/SKILL.md --print '<prompt>'`, adding the provider/model above. Exact prompts:

```text
Implement a responsive editorial and pricing page. There is no project type scale. Current CSS uses body 12px/14px, h1 22px/22px, 140-character prose lines, tiny 10px navigation, changing-width loading buttons, and a 20-slice pie chart. Read the relevant references named by the loaded skill. Give concrete CSS starting values and exact source-PDF values where present, explicitly distinguish PDF guidance from WCAG requirements, cover responsive/async/data states, and specify verification. Do not invent a design file or user-research result.
```

```text
A React checkout has placeholder-only fields, custom file upload with the native input removed, OTP auto-submit on every digit, a loading button that shrinks to spinner width, immediate full-page spinner, unlabeled icon buttons, mobile cards that omit critical table columns, and fixed 250ms animation under reduced motion. Read the relevant references from the loaded skill. Return a prioritized implementation correction with concrete HTML/CSS/behavior, preserve exact PDF timing/count guidance where relevant but identify it as heuristic rather than WCAG, and define state and verification gates. Do not claim tests were run.
```

Full response artifacts were not committed; these scores are reproducible diagnostic history, not revision certification. A prior no-tools probe could not load branch references and therefore declined to quote exact PDF values. That failure is retained: agents must read the branch named by `SKILL.md`; entry-file retrieval alone is insufficient for detailed implementation.

These probes test skill behavior, not product usability or WCAG conformance. Re-run them after material changes and retain failures.
