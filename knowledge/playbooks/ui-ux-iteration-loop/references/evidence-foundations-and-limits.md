# Evidence Foundations, Standards, and Misuse Boundaries

Use this reference when a psychology claim, numerical rule, accessibility assertion, or causal conclusion carries design weight. Prefer current standards and direct product evidence; do not turn a memorable law into fake precision.

## Authority, relevance, and inference

Do not collapse different evidence dimensions into one ranking. **Normative constraints**—applicable law, policy, accessibility target, platform contract, security, and privacy—bound every decision regardless of outcome movement. For **product-context relevance**, reproducible behavior, representative task observation, validated instrumentation, support, and operational evidence usually outrank general theory. For **causal attribution**, a credible controlled comparison is stronger than uncontrolled product movement. Established HCI/psychology mechanisms generate predictions; heuristics and patterns generate inspection questions; preferences, conventions, and anecdotes generate hypotheses. None proves that a mechanism caused this interface behavior.

When sources conflict, document scope, population, task, date, method, and whether the claim is normative, descriptive, predictive, or causal.

## Law-to-interface boundaries

| Concept | Defensible use | Misuse to reject |
|---|---|---|
| Fitts’s law | Predict target-acquisition time from size and distance for a defined pointing task | Explaining semantic hesitation, motivation, or all “interaction cost”; declaring one universal target size |
| Hick–Hyman relationship | Predict decision time under specified, reasonably comparable choices and practiced mappings | “Fewer options is always better”; deleting navigation without preserving information scent or expert access |
| Miller’s 7±2 | Historical finding about immediate-memory channel capacity under specific tasks | A universal maximum of seven menu items, cards, fields, or chunks |
| Working-memory limits | Predict errors when task-relevant information must be carried or transformed | Calling every dense screen “cognitive load” without identifying what must be remembered |
| Gestalt principles | Predict likely perceptual grouping from proximity, region, similarity, connection, continuation, or common fate | Treating visual grouping as proof of comprehension, meaning, or task success |
| Change blindness/selective attention | Predict missed changes outside current focus or under competing task demand | Assuming any unnoticed element needs animation or higher salience |
| Mental models/information scent | Predict route choice and expectation from prior knowledge and visible cues | Treating the designer’s conceptual model as the user’s, or asking leading “does this label make sense?” questions |
| Prospect theory/loss aversion | Generate hypotheses about reference points, certainty, and perceived loss | Manufacturing fear, false scarcity, sunk cost, or asymmetric cancellation pressure |
| Choice overload/satisficing | Match elimination, comparison, and good-enough strategies to task and stakes | Removing meaningful alternatives or interpreting fast choice as informed choice |
| Self-determination theory | Examine autonomy, competence, and relatedness as possible motivation conditions | Assuming points, streaks, social pressure, or more choice creates intrinsic motivation |
| Peak–end/negativity effects | Inspect whether consequential peaks, failures, and endings distort remembered experience | Ignoring the full journey or intentionally engineering a pleasant ending around a harmful process |
| Aesthetic-usability effect/halo | Predict that visual quality can influence perceived usability and credibility | Using ratings or polish to overrule observed errors and inaccessible behavior |
| Social proof, authority, reciprocity, commitment | Test truthful cues that may reduce uncertainty after users can evaluate the material choice | Fabricated testimonials, unearned badges, undisclosed sponsorship, coercive defaults, or exploiting invested effort |
| ELIZA effect | Predict anthropomorphic over-attribution to conversational systems | Implying sentience, certainty, empathy, or expertise the system does not possess |

## Accessibility standard boundary

[WCAG 2.2](https://www.w3.org/TR/WCAG22/) provides technology-independent, testable success criteria and recommends use of the current version. Conformance is a floor, not proof that every disabled user can complete the task. Record the exact level and criteria tested.

Relevant examples:

- [SC 2.5.8 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) specifies a 24×24 CSS-pixel minimum or spacing route with exceptions; larger targets can still be preferable. Do not confuse a conformance exception with usability.
- [SC 2.4.11 Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) requires focused components not be entirely hidden by author-created content; the stronger usability aim is fully visible focus.
- [SC 3.3.7 Redundant Entry](https://www.w3.org/WAI/WCAG22/Understanding/redundant-entry.html) reduces repeated entry within a process; browser autocomplete alone does not satisfy the content responsibility.
- [W3C COGA usable guidance](https://www.w3.org/TR/coga-usable/) extends beyond WCAG conformance for cognitive and learning disabilities and explicitly calls for involving real users.

Automated scans cannot establish complete conformance. Pair rules with manual keyboard, zoom/reflow, content/state, and relevant assistive-technology task checks.

## Research inference boundaries

- A qualitative study can expose mechanisms and severe failures; counts from a small convenience sample do not estimate population prevalence.
- Analytics can show sequence and scale only if events, exposure, identity, denominator, missingness, and schema versions are sound.
- Before/after movement is vulnerable to seasonality, novelty, learning, concurrent releases, and population changes.
- Statistical significance does not establish practical value, user benefit, or absence of harm.
- Absence of observed harm is weak evidence when affected people are excluded, failures are hard to detect, or guardrails mature later.
- A mechanism is strengthened when its predicted behavior changes and alternatives do not; it is not proven by attaching a law after the fact.

## Primary-source anchors and provenance

These anchors establish provenance, not automatic applicability:

- Fitts, 1954, “The information capacity of the human motor system in controlling the amplitude of movement,” DOI `10.1037/h0055392`.
- Miller, 1956, “The magical number seven, plus or minus two,” DOI `10.1037/h0043158`.
- Deci & Ryan, 2000, “The ‘What’ and ‘Why’ of Goal Pursuits,” DOI `10.1207/S15327965PLI1104_01`.
- Gray et al., 2018, “The Dark (Patterns) Side of UX Design,” DOI `10.1145/3173574.3174108`.

Citation metadata was verified; this reference does not claim a new systematic review of each literature. The supplied PDF and NN/g study guide remain secondary synthesis inputs. Product decisions still require evidence in the actual task and population.

## Claim check

Before using a rule, write:

```text
Claim and source:
Claim type: normative | descriptive | predictive | causal
Population/task/context:
Prediction for this interface:
Result that would weaken it:
Higher-authority constraint:
Observed evidence and limit:
Decision: apply | adapt | reject
```
