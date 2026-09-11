<!-- capsule-v2 -->
# Frontend design plan-critique — how does a design agent mechanically avoid templated output?

**Source:** anthropics/skills (Apache-2.0 example) `main@3b3fad96`; Codebase Memory `skills`. **Question:** What is the two-pass design process, what does the token-system plan contain, and which three default looks are named as forbidden defaults?

## Plan → counterfactual critique → build (`skills/frontend-design/SKILL.md`, whole file)
**Path/Symbol:** `skills/frontend-design/SKILL.md` — Process section (:29–39), Design principles (:15–27), Restraint/self-critique (:41–43), Writing-in-design (:45–55).
**Signature:** behavioral contract (no code): brainstorm compact design plan → self-critique against the generic default → revise → only then write code.
**Data Shape:** the plan is a four-part token system: **Color** (4–6 named hex values), **Type** (2+ roles: characterful display face used with restraint + complementary body + optional utility face), **Layout** (one-sentence prose concept + ASCII wireframes to compare options), **Signature** (the ONE element this page will be remembered by).

### Decisive source
```markdown
# :31 — the calibration denylist of AI-default looks
AI-generated design right now clusters around three looks:
(1) a warm cream background (near #F4F1EA) with a high-contrast serif
display and a terracotta accent; (2) a near-black background with a single
bright acid-green or vermilion accent; (3) a broadsheet-style layout with
hairline rules, zero border-radius, and dense newspaper-like columns.
...
Where it leaves an axis free, don't spend that freedom on one of these defaults.
# :35 — the counterfactual critique gate
if any part of it reads like the generic default you would produce for any
similar page (work through a similar prompt to see if you arrive somewhere
similar) ... revise that part, say what you changed and why.
```

**Flow:** pin the subject first if the brief is vague (one concrete subject, audience, page's single job — stated) → pass 1: draft the four-token plan in thinking → pass 2: run the counterfactual ("what would I produce for ANY similar brief?") and revise every part that matches, recording what changed and why → build exactly to the revised plan, deriving every color/type decision from it → restraint pass: spend boldness ONLY on the signature element, keep a silent quality floor (responsive to mobile, visible keyboard focus, reduced motion respected), screenshot and self-critique. Copy rules bind too: name from the user's side (notifications, not webhook config), active voice, action names persist through the flow ("Publish" button ⇒ "Published" toast), errors explain-and-direct without apologizing.
**Invariant:** The brief's explicit words ALWAYS win — including when the brief asks for one of the three default looks; freedom only exists on axes the brief leaves open, and those axes must not be spent on defaults. Structural devices (numbering/eyebrows/dividers) must encode something TRUE about the content — numbered markers only for real sequences. CSS specificity collisions (type selector vs element selector cancelling padding/margin) are the named build-time trap.
**Probe:** Content-only skill, no upstream tests. Deterministic anchors (executed this pass):
`grep -c 'near #F4F1EA' skills/frontend-design/SKILL.md` = 1;
`grep -c 'work through a similar prompt' skills/frontend-design/SKILL.md` = 1;
`grep -c '4–6 named hex values' skills/frontend-design/SKILL.md` = 1.

## Get live surrounding code
**Retrieve:** (BM25 graph search returns 0 for markdown-only skills here — content search resolves it)
```ts
await mcp.codebase_memory.search_code({ project: "skills", pattern: "work through a similar prompt", file_pattern: "*.md", limit: 5 });
```
→ hits `skills.skills.frontend-design.SKILL` :35 (observed live this pass; `search_graph` query "frontend design generic default signature" totals 0 — recorded as the adversarial-miss example).

## Verdict
Adopt: two-pass plan/critique with an explicit negative-pattern denylist and a one-signature-element budget; token-system plan shape; copy-as-interface vocabulary rules. Adapt: the specific three looks as your host's calibrated defaults drift (re-derive them empirically); hex palette counts to your design system. Omit: nothing structural — this is pure behavioral guidance with no vendor API surface.
