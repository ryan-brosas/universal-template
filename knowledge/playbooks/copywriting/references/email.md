# Email and Sequences

Load this capsule for campaign, lifecycle, onboarding, launch, nurture,
abandoned-cart, reactivation, cold-outbound, or sales emails. Load
`messaging-positioning.md` first when the reader, dominant value, or belief
inventory is undecided. This capsule owns channel expression and flow design.
`editing-validation.md` owns test methodology.

## Scope and handoffs

Start from accepted inputs or label their absence:

- approved reader, value, and beliefs per route;
- customer language, objections, and proof from research;
- offer terms, prices, deadlines, and guarantees;
- product states, events, and available triggers;
- list size, ESP capabilities, and consent status;
- existing flows, baselines, and performance.

Deliverables are a flow map, tag dictionary, per-email drafts with job and send
condition, claim ledger, and metric plan. Destination pages are owned by
`pages.md`; check promise continuity at every link.

## Map the flow before writing

Model each automation as a state machine:

```text
recipient state + trigger → one job → action/inaction branch → next state
```

Draw the map outside the CRM. Native automation views hide conditional logic.
For every node record:

- entry trigger and segment gate;
- fixed or conditional delay;
- one behavioral job;
- CTA and its destination;
- exit branches for action, inaction, and exit;
- terminal state or named successor.

Run these checks on the map:

- **Black holes:** every terminal state names the next automation or an explicit
  end-of-journey reason. A lead who exits a nurture flow without converting must
  enter a retention pool or re-engagement queue, not nothingness.
- **Consent gate:** declare the consent basis (double opt-in, single opt-in,
  existing customer relationship) and confirm every downstream send respects it.
  If later emails hinge on confirmed opt-in, say so.
- **Cadence:** record inter-email intervals explicitly. Flag intervals that
  exceed the likely attention window for that lifecycle stage.

| Condition | Action |
|---|---|
| More than 30% of states are black holes | rebuild the skeleton; keep individual copy as candidates |
| Consent gate missing or bypassed | stop sends; fix the gate before any copy work |
| One edge's gap exceeds the stage window by 2x | patch that edge's delay; do not rewrite adjacent emails |
| Two or fewer states and no branching | broadcast masquerading as automation; redesign as a state machine |

## Triggers and timing

Tag every trigger as **action** or **inaction**.

- Action triggers: clicks, registrations, purchases, logins, form events.
- Inaction triggers: require a named observation window and a minimum-signal
  threshold (N consecutive missed opens, not a single miss). Span at least two
  local business days to avoid timezone false positives.

Document every delay as **fixed** (48 hours after cart abandonment) or
**conditional** (until next login, capped at 7 days). Conditional delays need a
cap so a recipient cannot suspend a flow indefinitely.

Deduplicate overlapping triggers: when two triggers can fire for the same
recipient in the same window, define priority and mutual exclusion. This
prevents three reminder emails in one afternoon.

Stopping rules:

| Signal | Rule |
|---|---|
| Target action completed | suppress remaining emails in that flow; route to the post-action state |
| Unsubscribe or spam complaint | suppress marketing and other consent-based flows immediately; honor legal/channel suppression rules; do not send a marketing apology. Required transactional, confirmation, receipt, password-reset, and support messages may still send when law, contract, or product safety requires them |
| Escalation cap reached with no response | enter a pause state; set a re-engagement trigger with a cooldown before the next attempt |
| Purchased or completed state | suppress upsell and reactivation for that product; keep support and relevant cross-sell |

For disengaged active users, use the **escalate, pause, resume** pattern:
escalate reminders to a cap, then send an honest pause email that stops
notifications. Resume on a re-engagement signal. No guilt, no pretending the
user owes an explanation.

## Segmentation and suppression

Segment only when treatment changes: job, CTA, proof, or offer. A name merge
tag is personalization, not segmentation. Combine declared intent with observed
behavior; a click alone does not explain motivation.

Maintain a **tag dictionary** alongside the flow map. For each tag record name,
definition, how it is set (event, manual, score), which flows read it, and which
flows write it. Document meaning explicitly; the ESP will not interpret it for
you.

- **Suppression inheritance:** a suppressed parent segment (purchased Product X)
suppresses child segments unless the override is documented.
- **Marketing vs transactional:** list-unsubscribe and spam complaints suppress
  marketing and nurture flows. Transactional, receipt, security, and required
  service messages follow separate rules and may still send when legally or
  operationally required.
- **Segment triage:** fold a segment into its parent with a conditional block
  when the only difference is a merge tag. Split a segment that mixes roles
  with materially different jobs.
- **Sales alignment:** when a sales team consumes the list, the scoring rubric
  references the same behavioral events the flow uses. Divergence means the flow
  optimizes one metric while sales prioritizes another.

| Question | If yes | If no |
|---|---|---|
| Does treatment change? | create or keep the segment | use a conditional block in the parent |
| Is the difference consequential (role, use case, stage, purchase)? | segment | do not segment on cosmetic differences |
| Can the ESP express it as tag plus condition? | prefer tags over static segments | use a static segment |
| Does it overlap another segment with conflicting treatment? | define priority or mutual exclusion | no action |

## One email, one job

The job may be to confirm signup, learn intent, reach the first value moment,
teach one useful behavior, answer one objection, supply proof, restore an
interrupted path, or invite evaluation, purchase, or reply. Two distinct jobs
mean two emails.

Match commitment to readiness:

| Readiness signal | CTA type | Example |
|---|---|---|
| Just signed up, no product interaction | call to value | “Pick your first template” |
| Opened product, core action incomplete | activation nudge | “Finish connecting your calendar (2 min)” |
| Core action done, trial midpoint | depth or expansion | “Try the reporting view” |
| Trial ending, high engagement | direct upgrade | “Keep your workspace, start the paid plan” |
| Trial ending, low engagement | evaluation aid plus honest terms | “Here is what you built. Here is what paid adds. Your trial ends [date].” |

Repeat one semantic CTA when length requires it. Never add competing actions.
Early readers get lower-resistance calls to value; ready readers get the direct
ask. Do not disguise a purchase request as a low-commitment click.

## Subject, preview, and body craft

Subject strategy by sequence role:

| Role | Strategy | Avoid |
|---|---|---|
| Welcome or confirmation | name what they signed up for; set expectation | hype, generic “Welcome!” |
| Onboarding or activation | reference their specific action or inaction | feature dumps, multiple asks |
| Trial end or evaluation | name the decision they face | manufactured countdowns, guilt |
| Abandoned cart | name the item or category; reduce friction | discount as the first word |
| Reactivation or cold | short, personal, question form | long subjects, multiple topics |
| Launch or promotion | lead with the outcome or mechanism | “We are excited to announce” |

Preview text gets roughly 40 to 90 characters. It must add a fact, question, or
contrast the subject does not carry. Never repeat the subject. Boilerplate such
as “View in browser” wastes the slot; an empty preheader is less harmful than a
redundant one.

Body craft rules:

- **Text-first default.** Recipients say they prefer images but engage more
  with text-heavy, image-light sends. Use an image only when it carries
  information a sentence cannot.
- **Cap sentences at 20 words.** Split compound sentences that shift topic. One
  idea per sentence.
- **Front-load.** The most decision-relevant fact (price, deadline, what happens
  next) appears in the first two body sentences, not after a preamble.
- **Specificity.** Every CTA, link, and subject names a concrete object or
  outcome. “Your invoice for March” beats “Update inside.”
- **Novelty decay.** Track formula reuse. A subject structure that outperforms
  twice decays on the third use. Rotate structural patterns, not just wording,
  and log the usage count in the sequence notes.
- **Best-practice mediocrity test.** Before finalizing, ask whether this email
  says something specific to this recipient at this moment, or would work
  unchanged for a different audience. If the latter, revise. Checklist compliance
  is necessary but not sufficient.

## CTA craft

- **“I want to” completion test:** the CTA text should complete “I want to
  ___” naturally. “See my dashboard” works; “Click here” does not.
- **Specific copy per variant:** when multiple CTAs appear (variant selection,
  plan choice), each names the specific item, quantity, or price. Identical CTA
  text for different destinations is a defect.
- **One primary CTA per email.** Secondary footer links are structural, not
  persuasive.
- **Post-click expectation:** the sentence immediately after the CTA states what
  happens on click (“You will land on your project dashboard, no setup
  needed”). This reduces click anxiety.
- **Format:** default to a single text link styled as a sentence fragment for
  onboarding and reactivation. Reserve buttons for transactional or
  high-commitment CTAs. Test both; do not assume buttons convert better.
- **Placement:** the primary CTA appears within the first screenful. Repeat it
  at the end when the email exceeds one screen.

## Sequence playbooks

### Welcome and trial onboarding

Send only the jobs the user still needs, in state order:

1. **Welcome and orient:** confirm the reason for signup, set frequency
   expectations, offer controls, give the smallest useful first action. Ask one
   self-segmenting question (“Which matters first: reporting, handoffs, or
   planning?”).
2. **Learn intent:** deliver the promised resource; connect declared intent to
   the next step.
3. **Value moment:** guide to an observable first value; reference their actual
   setup state.
4. **Barrier:** address one common barrier with process guidance or relevant
   proof (a success story, quantified evidence).
5. **Re-entry:** on actual inactivity, acknowledge the interruption, reconnect
   to the original intent, give a direct resume path. No shame, no pretending to
   know why they stopped.
6. **Evaluation:** before trial end, help them evaluate: what they built, what
   paid adds, real terms, and the no-card truth when it applies.

Cadence sanity ranges are descriptive, not rules: a 14-day trial typically sees
4 to 6 sends; a 30-day trial 6 to 10. Deviation requires a stated reason tied to
state changes, not habit. Use escalate, pause, resume for disengagement inside
the trial.

### Launch or promotion

Cover the decision case across messages: relevance, problem or opportunity,
mechanism, proof, objections, offer, and real deadline. Branch opened/no-click,
clicked/no-conversion, and converted users when reliable data supports it.
Exclude purchasers. State specific, verifiable constraints; never manufacture
scarcity or countdowns.

### Abandonment

Diagnose before writing: checkout defects, forced registration, unclear fees,
missing payment options, and technical failures. Strong copy cannot repair a
broken checkout. Then match touches to the likely barrier without asserting why
the person stopped:

- **Touch 1:** return path, no discount. “Your cart is saved. Pick up where you
  left off.”
- **Touch 2:** factual risk reduction (shipping, returns, fees, reservation
  window).
- **Touch 3, when justified:** human help or a truthful constraint.

A discount is a hypothesis that price is the barrier, not the default fix. Test
it against a documented baseline.

### Reactivation

Brief, low-pressure, honest. Use a short personal question form. Offer a direct
re-entry path or a reply path. A final touch may state archive intent honestly
(“Quick question before I archive your spot”). Stop after the final touch or on
any reply.

### Cold or outbound

Selling is a conversation, not a pitch. Pattern:

1. Short, personal, references a specific trigger or shared context.
2. One question or one small ask, not a pitch.
3. Easy reply path.
4. Follow-up cadence of 2 to 3 touches over 2 to 3 weeks, each adding one new
   piece of relevant information.
5. Stop after the final touch or on any reply.

The nine-word form (“{Name}? Are you still looking for {thing}?”) works because
it is a question, not an ad.

### Ongoing list rotation

For lists receiving more than one email per month, rotate sales, nurture, and
engagement messages (for example 1:2:1 per month). All-sales rotation causes
fatigue. For products with infrequent use, designate one recurring newsletter
slot whose job is relevance and community, not selling. Tailor it to a segment;
do not blast.

## Deliverability and accessibility constraints

Copy-level rules that protect the message. Sender reputation, SPF/DKIM/DMARC,
and list hygiene belong to operations; flag them when diagnosing delivery
problems instead of blaming copy.

- **Plain-text fallback carries the full argument.** Test with images blocked:
  subject, preview, body, and CTA must stay legible and persuasive.
- **Images:** at most one relevant image per email; descriptive alt text (what
  it shows plus why it matters); no baked-in text; no GIFs; no decorative
  backgrounds.
- **Links:** no URL shorteners; five or fewer body links; every link resolves
  before send (never point at a future landing page); HTTPS; consistent UTM
  parameters; unsubscribe visible and functional.
- **Spam-trigger review:** no ALL-CAPS words; at most one exclamation mark in
  the subject; urgency words only when true and rarely; no stacked hype
  phrases; test merge tags with a subscriber missing the field so no raw
  `{{first_name}}` ships.
- **Mobile:** the core point lands in the first sentence after the greeting;
  paragraphs run three sentences or fewer; the CTA sits within the first
  screenful; single column.
- **Accessibility:** descriptive link text (never “click here”); logical heading
  order; complete plain-text version; no content conveyed by color alone.

## Metrics and diagnosis

Metric per job:

| Job | Primary metric | Harm signals |
|---|---|---|
| Welcome or orientation | first action completion | unsubscribe, bounce |
| Activation | key behavior event | inactivity past the window |
| Proof or objection handling | click to the relevant page | spam reports |
| Purchase or upgrade | completed conversion | cart abandonment, refund |
| Reactivation | re-engagement event | unsubscribe |

- Opens are noisy diagnostics (privacy distortion). Use them for gross
  anomalies, not benchmarks.
- Clicks indicate movement, not final conversion. Judge the email against its
  intended action and the downstream outcome.
- Unsubscribe and spam rates are harm signals that override click gains.
- Compare against a documented baseline before rewriting from taste. An
  existing email is a baseline, not a proven control.
- Diagnose at flow level first: find the first observed break (healthy opens but
  low qualified clicks; cart reached but payment stalls), then inspect that node
  and the previous one or two handoffs. The visible breakpoint may expose an
  upstream promise mismatch.
- Last-touch attribution over-credits the final email. Multi-email journeys need
  journey-level analysis before crediting one message.
- When to stop sending: escalation cap reached, unsubscribe, complaint,
  purchased state, or failed re-engagement. Silence is a designed state, not a
  bug.

## Governance

- Store the versioned flow map alongside the sequence config. A copy change
  without a map change is suspect.
- Keep the tag dictionary current; every tag has an owner and definition.
- Keep a claim ledger for emails: claim, evidence, scope, prohibited
  overstatement, status. The HARD-GATE in `SKILL.md` applies per email.
- Keep a formula log: subject structures in use and their reuse counts.
- Review triggers: product state changes, offer changes, new segments, complaint
  spikes, cadence drift, ESP migration.
- Statuses: `draft`, `conditional`, `approved for send`, `deprecated`. Approved
  does not mean market-validated.

## Stopping rules

| Stage | Stop when | If not satisfied |
|---|---|---|
| Flow map | every node has a trigger, job, and successor or documented exit | fix the map before drafting |
| Triggers | every trigger is tagged; inaction triggers have windows and caps | mark assumed; do not schedule |
| Segments | treatment differs and tags are documented | fold into the parent |
| Job | one behavioral job per email | split the email |
| Craft | specificity, novelty, and audience-specificity tests pass | revise before scheduling |
| Claims | every claim has evidence or a placeholder | hold the send |
| Metrics | primary metric and harm signals are named | do not claim optimization |

## Acceptance checklist

- [ ] Flow map exists outside the CRM; no black holes; consent gate explicit;
      cadence recorded.
- [ ] Every trigger is tagged action or inaction with a window and cap where
      needed.
- [ ] Stopping rules implemented: action complete, unsubscribe, purchase,
      escalation cap.
- [ ] Segments change treatment; tag dictionary current; suppression
      inheritance verified.
- [ ] Each email has one job, one primary CTA, and commitment matched to
      readiness.
- [ ] Subject names a concrete object or outcome; preview adds new information.
- [ ] Body passes the 20-word cap, front-loading, and audience-specificity
      tests.
- [ ] CTA completes “I want to ___”; post-click expectation stated.
- [ ] Plain-text fallback carries the argument; images-blocked test passes.
- [ ] Link audit: no shorteners, all links resolve, UTM consistent, unsubscribe
      works.
- [ ] Primary metric, harm signals, and baseline documented per email.
- [ ] No invented testimonials, statistics, deadlines, scarcity, or
      capabilities.
