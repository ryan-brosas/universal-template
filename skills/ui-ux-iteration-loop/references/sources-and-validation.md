# Sources, Synthesis Boundaries, and Validation

## Sources read

1. Victor Ponamariov, *100 Practical UI/UX Tips* (108-page PDF, creator metadata Victor Ponamariov; PDF creation metadata 2021). The supplied local copy was read in full. It organizes practical examples across typography, forms, validation, landing pages, usability, visuals, loading/empty states, attention, navigation, accessibility, and data-heavy edge cases. Its closing principle—research and iterate because rules have exceptions—is the process’s controlling idea.
2. Tanner Kohler, [“Psychology for UX: Study Guide”](https://www.nngroup.com/articles/psychology-study-guide/), Nielsen Norman Group, published January 10, 2024. The supplied page was retrieved in full. It maps UX psychology across attention, Gestalt perception, memory, sensemaking, choice, motor interaction, motivation, practitioner cognitive biases, persuasion/trust, emotion/delight, and attitudes toward technology.
3. [WCAG 2.2](https://www.w3.org/TR/WCAG22/), W3C Recommendation, plus W3C understanding material for [Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Focus Not Obscured](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html), and [Redundant Entry](https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry.html), and [COGA usable guidance](https://www.w3.org/TR/coga-usable/). These establish testable accessibility requirements and supplemental cognitive-accessibility guidance, not a substitute for task testing with affected people.
4. Primary-source provenance was checked for Fitts (1954, DOI `10.1037/h0055392`), Miller (1956, DOI `10.1037/h0043158`), Deci & Ryan (2000, DOI `10.1207/S15327965PLI1104_01`), and Gray et al. (2018, DOI `10.1145/3173574.3174108`). Their metadata anchors the concepts; it does not make a result automatically applicable to a new task or population.

The NN/g page is a curated study map, not evidence that every linked effect explains a particular interface. To deepen the synthesis, 53 linked NN/g articles were retrieved across attention, Gestalt grouping, memory, sensemaking, decision strategies, interaction cost, motivation, practitioner bias, persuasion, trust, delight, AI anthropomorphism, and digital wellbeing. The detailed reading reinforces several controlling distinctions: user error often reflects design conditions; external memory beats recall burden; options require different support for elimination versus comparison; trust must precede commitment; and delight rests on functional, reliable, usable behavior. This does not claim independent review of every linked video, book, paid course, or primary study.

## Critical synthesis

The PDF is strongest as a broad inspection checklist and pattern library. Some recommendations are context-dependent, numerically approximate, or superseded by a project’s current standards. The skill therefore retains the user problem behind each tip but converts prescriptions into hypotheses and checks. WCAG and platform behavior outrank informal contrast, timing, target, and accessibility advice.

The psychology guide is strongest as a mechanism map. Its categories prevent shallow “cognitive load” explanations, but naming an effect after observing a symptom creates a just-so story. The loop separates observation, competing explanations, intervention, and comparative evidence. It also applies cognitive-bias checks to practitioners, not merely users.

Combined, the sources support this chain:

```text
user task → baseline → observed break → plausible mechanism
→ smallest coherent intervention → state/accessibility checks
→ behavioral comparison → keep/revise/revert → next unknown
```

The ethical boundary is explicit because the same psychology can support autonomy or exploit bias. User comprehension, control, reversal, trust, and downstream welfare are guardrails. Measurement integrity is also a product-safety concern: a broken denominator, event schema, or excluded population can turn a dashboard into a mechanism for scaling harm.

## Behavioral validation

`behavior-evaluations.md` owns the adversarial suite and hard-fail rules. It tests ambiguous instrumentation, high-stakes automation, zero-evidence greenfield work, inaccessible incidents, deceptive pressure, competing explanations, implementation detail, affected segments, delayed guardrails, and explicit stop/escalation decisions.

`behavior-evaluation-results.md` records revision-bound RED/GREEN history, invocation, rubric evidence, and limitations. Its listed probes are historical rather than a current certification because they lack a retained full response artifact and Git revision; they demonstrate only procedure-following by the tested model under those prompts, not product validity or universal model behavior. Re-run with a different model or reviewer after material changes.
