# Research and Voice of Customer

Load this capsule when customer material exists, inputs are weak, or the message
must be discovered rather than polished. The output feeds
`messaging-positioning.md`. It is not a page outline, email sequence, test plan,
or framework assignment.

## Evidence ladder

Prefer evidence closer to real decisions:

1. Recent customer interviews and observed behavior
2. Sales calls, support tickets, objections, churn and win-loss notes
3. On-site surveys, search queries, chat logs, usability sessions
4. Verified testimonials and reviews of this product
5. Reviews of alternatives used by the same audience
6. Competitor pages and internal stakeholder beliefs

Lower levels can suggest hypotheses. They do not overrule direct customer
evidence. Analytics shows where behavior changed, not why.

Collection surfaces and their roles:

| Surface | Role |
|---|---|
| Customer interviews | recover decisions, language, and motivation in depth |
| Surveys and on-page prompts | scale up patterns and completion phrases |
| Thank-you pages | capture language while the experience is fresh |
| Support tickets | reveal failures, workarounds, and resolution that satisfied |
| Sales calls | capture live objections and resolution state |
| Churn and win-loss notes | separate anxieties from differentiators |
| Reviews and testimonials | mined proof and recurring outcomes |
| Competitor pages | category language and unaddressed pains |

Two reconciliation rules:

- **Stated versus actual:** an intake item that records only what a customer
  says they want is incomplete. Pair it with observed behavior or a behavioral
  proxy. Flag items where statement and action diverge.
- **Source conflict:** when two sources disagree, the lower-ladder source cannot
  overrule the higher one, but the disagreement itself is a hypothesis worth
  logging in the unknowns list.

## Intake and triage

Record what is known about:

- audience and buying role;
- triggering situation and current alternative;
- desired progress and concrete outcome;
- offer, mechanism, constraints, price, and next action;
- recurring anxieties, objections, failed attempts, and decision criteria;
- proof available and claims prohibited;
- source, date, segment, and confidence for each item.

Assign every item a confidence tier:

| Tier | Criteria |
|---|---|
| Low | 1 to 2 sources, self-reported, or older than 12 months |
| Medium | 3 to 5 sources, mixed verification, under 12 months |
| High | 6 or more sources, at least 2 verified, under 6 months, consistent across segments |

A fragment needs at least three independent sources (different people, different
sessions) before it graduates from hypothesis to working message. A single vivid
story is a seed, not a conclusion. Exception: a specific purchase-blocking
objection from a high-value segment member starts at Medium, because its
consequence (a lost sale) is known even when its frequency is not.

Use the **ask, document, feed** loop when existing material is thin: solicit the
audience's own words directly (“What do you want from a tool like this?”),
document them verbatim, then feed those words back into copy. Solicitation beats
mining when the corpus is empty; mining beats solicitation when the corpus is
rich.

Stop collecting for a segment when any of these holds:

- the last three new fragments produce no new tags;
- the top five ranked messages have not changed in two consecutive passes;
- a hard cap is reached (about 15 interviews per segment).

If critical inputs are missing, ask only for material that could change the
message. When the user wants a draft now, produce a bounded draft with explicit
placeholders and a short evidence request.

## Interview design and execution

Ask about a recent event, not a hypothetical preference:

1. “Take me back to the last time [problem happened]. What was going on?”
2. “What did you try first? Then what?”
3. “What made the old way unacceptable?”
4. “Which alternatives did you consider, and what worried you about each?”
5. “What almost stopped you from choosing this?”
6. “What changed after you started?”
7. “How would you describe the product to a colleague?”

Construction rules for new questions:

- Build them from the 5-Ws: who, what, when, where, why, plus how. A question
  missing a temporal anchor (“when,” “the last time”) tends to collect opinions
  instead of decisions.
- Anchor on the moments leading up to the decision, then drill one level below
  the stated task. “I needed hot water” drills down to “I wanted a hot drink in
  under a minute.” The job lives below the task.
- Rephrase before replace: if a drafted question is closed, rephrase it open
  before discarding it. Retire a question only after its wording has been tried
  in at least one live session.

Open versus closed, mid-interview:

| Goal | Mode |
|---|---|
| Sequence, language, motivation, context | open |
| Quantities, durations, frequencies | closed |
| Known comparisons (“did you use X or Y?”) | closed |
| Anything about feelings or reasons | open, then quantify with a follow-up closed question |

Do not lead the witness toward the feature. Deploy the same proven questions
across surfaces: interviews, surveys, thank-you pages, and on-page prompts.
Revise wording after observing response quality, not before.

## Review and social-proof mining

Capture short fragments in a table:

| Fragment | Source/segment | Situation | Pain or desire | Objection | Outcome | Objective served | Verification | Strength |
|---|---|---|---|---|---|---|---|---|

Tag fragments by:

- **trigger:** why action began now;
- **before:** old process, cost, emotional or social tension;
- **after:** observable progress and desired identity;
- **selection:** alternative, criterion, differentiator;
- **anxiety:** risk, trust gap, setup cost, hidden downside;
- **language:** vivid noun, verb, analogy, or repeated phrase;
- **proof:** quantified result, specific story, mechanism, demonstration;
- **objective served:** which job this fragment does for copy (see below).

Record verification status for every fragment: verified buyer, self-reported,
or third-party. Unverified fragments get a lower confidence weight.

Nine testimonial objectives. Tag each fragment against the one it serves:

1. establish credibility;
2. signal buyer type (“people like me”);
3. borrow authority;
4. reinforce a delighter;
5. stomp a specific objection;
6. add an emotional layer;
7. trigger the herd (“most teams choose”);
8. show a personal face;
9. confirm fit for a situation or location.

Social proof types beyond testimonials, each with a different mechanism: user
counts, rating aggregates, verified-buyer reviews, case studies, embedded
mentions, third-party endorsements, stock or supply signals, and tool or AI
outputs. Do not treat them as interchangeable decoration.

Two placement rules:

- **Ambivalence condition:** social proof moves readers who are conflicted or
  undecided. It is weak or redundant for already-committed buyers. Tag each
  fragment with the reader state it serves.
- **Decision-point power:** proof near the decision point (CTA, pricing,
  signup) carries more weight than proof buried in body copy.

Purposeful solicitation: know what you need from a testimonial before asking.
If a collected testimonial misses the objective, go back for a revision instead
of stretching it. Never manufacture a composite quote.

## Support-ticket and sales-call mining

- **Ticket-cluster pass:** group tickets by triggering situation, failed
  attempt, and the resolution that satisfied the user. Each cluster becomes a
  candidate fragment row. Clusters with repeated failed attempts are anxiety
  gold.
- **Sales-call objection log:** for every call, record the exact objection
  phrase, its context (price, timing, competitor), and whether the rep resolved
  it. Unresolved objections are high-value anxiety fragments.
- **Win-loss delta:** compare language in win notes versus loss notes. Phrases
  that appear in losses but not wins are candidate anxieties. Phrases in wins
  but not losses are candidate differentiators.

## Competitor and alternative mining

- **Alternative-comparison matrix:** one row per named alternative per
  interview. Capture why it was considered, the specific worry, what made the
  chosen option win, and the switching cost mentioned.
- **Competitor-page scan protocol:** read the value proposition, headline, first
  CTA, and the top three objections addressed. Log what the competitor claims
  (level 6, unverified) separately from what its own customer reviews confirm
  (level 5).
- **Gap identification:** list pains and anxieties that appear in your customer
  data but are unaddressed on the competitor's page. These are positioning
  opportunities, not yet claims.

## Message-mine scoring

Rank candidates by:

1. recurrence across independent sources;
2. emotional force;
3. specificity;
4. closeness to the buying decision;
5. fit with the target segment;
6. **“I want ___” completion:** how naturally the fragment completes “I want…”,
   “I wish someone could…”, or “If only there was…”. High-completion fragments
   are ready-made headlines and CTAs;
7. **awareness-stage fit:** a fragment that resonates with problem-aware
   prospects may be irrelevant to most-aware buyers. Tag each fragment with the
   stage(s) it serves; do not rank across stages without weighting;
8. **skeptic resonance:** does the fragment speak to a fence-sitter, or only to
   someone who already agrees? Fragments that only confirm believers score lower
   for acquisition copy.

Gates before ranking finalizes:

- **Plausibility gate:** a fragment becomes a claim only when it is true, not
  merely plausible. Flag plausible-but-untrue material and exclude it.
- **Confirmation-bias check:** before finalizing the top five messages, actively
  search the corpus for fragments that contradict each item. If a contradiction
  exists and is not explained by segment difference, demote the item.
- **Ethical red line:** reject any fragment whose natural use requires a
  guilt-trip frame (“Don't you want…?”) or a misleading cherry-pick. Log it as
  excluded-ethical so the team sees it was considered and rejected.

## Phrase-bank construction

- **Seed from completions:** run the “I want / I wish / If only” prompts in
  interviews and surveys. Collect the completed phrases verbatim. These form the
  first tier of the bank.
- **Three fidelity levels.** Label every entry:
  - verbatim quote: needs attribution and full fidelity;
  - structural echo: your sentence built on the customer's exact noun or verb,
    light editing allowed;
  - paraphrase: their meaning in your words.
- **Fidelity rules:** if the phrase enters a testimonial or attributed quote,
  fidelity is required. If it enters your copy as a structural echo, light
  editing is allowed. If it enters a headline or CTA, the “I want ___”
  completion form takes priority over the original syntax.
- **Deduplicate:** group phrases by tag. Within a cluster, keep the two or three
  highest-scoring variants and discard near-duplicates.

## Claim-and-proof inventory

For each claim, record:

- **Proof type:** quantified result, specific story, mechanism explanation,
  demonstration, verified-buyer review, user count, rating aggregate, case
  study, or third-party endorsement. A claim with no proof type assigned is a
  hypothesis, not a claim.
- **Verification status:** verified (customer confirmed, timestamped),
  self-reported, third-party, or internal. Self-reported proofs get a discount.
- **Scope and qualifier:** segment, period, condition.
- **Placement note:** where the pair will live. Objection-stomping claims go
  near the friction point (pricing, signup, the feature in question).
- **Proof-gap flag:** if a desired outcome appears in customer language but no
  proof exists, flag it as a research gap, not a claim. Naming the gap honestly
  can work, but only if you follow through.

## Bias control

- **Stated-only discount:** for every desired-progress or anxiety item, ask
  whether a behavioral observation confirms or contradicts it. If not, mark the
  item stated-only and discount it.
- **Awareness-stage contamination:** do not mix fragments from unaware prospects
  with fragments from most-aware buyers in the same ranking pool. They answer
  different questions.
- **Scanner-versus-reader weighting:** if the primary channel is scanned, weight
  short high-force fragments above long narrative ones. If the channel is read
  (long-form email, sales page), narrative fragments gain weight. Match fragment
  length to expected attention mode.
- **Recency check:** discount fragments older than the product state they
  describe. A pain from a previous version may no longer exist.

## Handoff to messaging-positioning

The VoC package is ready for handoff only when:

- [ ] One Reader and triggering context are specified, not generic.
- [ ] Each of the top three pains has at least two supporting fragments.
- [ ] Every claim in the inventory has a proof type or a gap flag.
- [ ] The phrase bank holds at least ten entries spanning at least four of the
      seven tags.
- [ ] At least one objection is tagged purchase-blocking.
- [ ] The unknowns list is non-empty. An empty unknowns list means the research
      was too shallow.

Deliver with the package:

- **Lead-with recommendation:** based on the dominant awareness stage, whether
  positioning should lead with product, want, or problem. Positioning can accept
  or override it.
- **Objection-placement map:** pairs of objection and recommended location, so
  downstream copy knows where rebuttals belong, not just what they say.
- **CTA seed list:** the three to five strongest “I want ___” completions,
  labeled as CTA or call-to-value candidates.
- **Explicit non-handoff:** no page structure, email sequences, test plans, or
  framework assignments. Those belong to their own capsules.

## Stopping rules

| Stage | Stop when | If not satisfied |
|---|---|---|
| Collection | saturation, stable top five, or cap reached | keep collecting; do not rank |
| Triage | every item has source, date, segment, tier | mark Low; request verification |
| Interviews | decisions recovered, not opinions collected | re-anchor on recent events |
| Mining | fragments tagged with objective and verification | re-run the tagging pass |
| Scoring | gates passed (plausibility, bias, ethics) | demote or exclude items |
| Handoff | acceptance checklist complete | return to the failing stage |
